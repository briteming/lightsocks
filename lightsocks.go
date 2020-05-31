package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/rand"
	"net"
	"os"
	"os/user"
	"path"
	"reflect"
	"strconv"
	"strings"
	"time"

	"github.com/mitnk/goutils/encrypt"
	"github.com/orcaman/concurrent-map"
)

var VERSION = "1.7.0"
var countConnected = 0
var KEY = getKey()
var DEBUG = false

type GoixyConfig struct {
	Key        string
}
var GC GoixyConfig = GoixyConfig{}

var Servers = cmap.New()

func main() {
	host := flag.String("host", "0.0.0.0", "host")
	port := flag.String("port", "12345", "port")
	_debug := flag.Bool("v", false, "verbose")
	flag.Usage = func() {
		fmt.Printf("Usage of lightsocks v%s:\n", VERSION)
		fmt.Printf("lightsocks [flags]\n")
		flag.PrintDefaults()
		os.Exit(0)
	}
	flag.Parse()
	remote, err := net.Listen("tcp", *host+":"+*port)
	if err != nil {
		fmt.Printf("net listen: %v\n", err)
		os.Exit(2)
	}
	defer remote.Close()
	DEBUG = *_debug

	info("lightsocks v%s", VERSION)
	info("listen on %s:%s", *host, *port)

	go printServersInfo()
	for {
		local, err := remote.Accept()
		if err != nil {
			info("error when accept: %v", err)
			continue
		}
		go handleLocal(local)
	}
}

func printServersInfo() {
	for {
		select {
		case <-time.After(600 * time.Second):
			ts_now := time.Now().Unix()
			keys := Servers.Keys()
			info("[REPORT] We have %d servers connected", len(keys))
			for i, key := range keys {
				if tmp, ok := Servers.Get(key); ok {
					bytes := int64(0)
					ts_span := int64(0)
					if tmp, ok := tmp.(cmap.ConcurrentMap).Get("bytes"); ok {
						bytes = tmp.(int64)
					}
					if tmp, ok := tmp.(cmap.ConcurrentMap).Get("ts"); ok {
						ts_span = ts_now - tmp.(int64)
					}

					str_bytes := ""
					if bytes > 1024*1024*1024 {
						str_bytes += fmt.Sprintf("%.2fG", float64(bytes)/(1024*1024*1024))
					} else if bytes > 1024*1024 {
						str_bytes += fmt.Sprintf("%.2fM", float64(bytes)/(1024*1024))
					} else {
						str_bytes += fmt.Sprintf("%.2fK", float64(bytes)/1024)
					}

					str_span := ""
					if ts_span > 3600 {
						str_span += fmt.Sprintf("%dh", ts_span/3600)
					}
					if ts_span > 60 {
						str_span += fmt.Sprintf("%dm", (ts_span%3600)/60)
					}
					str_span += fmt.Sprintf("%ds", ts_span%60)
					info("[REPORT] [%d][%s] %s: %s", i, str_span, key, str_bytes)
				}
			}
		}
	}
}

func handleLocal(local net.Conn) {
	countConnected += 1
	defer func() {
		local.Close()
		countConnected -= 1
		debug("closed local")
	}()

	debug("local connected: %v", local.RemoteAddr())
	buffer := make([]byte, 1)
	_, err := io.ReadFull(local, buffer)
	if err != nil {
		info("cannot read first byte from local")
		return
	}
	buffer = make([]byte, buffer[0])
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		info("cannot read validation data from local")
		return
	}
	dataCheck, err := encrypt.Decrypt(buffer, KEY)
	if err != nil {
		info("invalid local: %v", err)
		return
	}
	if !reflect.DeepEqual(KEY[8:16], dataCheck) {
		info("invalid local: checker types not eq")
		return
	}
	buffer = make([]byte, 1)
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		info("cannot read size from local")
		return
	}

	buffer = make([]byte, buffer[0])
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		info("cannot read host from local")
		return
	}
	host, err := encrypt.Decrypt(buffer, KEY)
	if err != nil {
		info("ERROR: cannot decrypt host")
		return
	}

	buffer = make([]byte, 2)
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		info("cannot read port from local")
		return
	}
	port := binary.BigEndian.Uint16(buffer)

	url := net.JoinHostPort(string(host), strconv.Itoa(int(port)))
	if strings.Contains(url, "[[") && strings.Contains(url, "]]") {
		// not known yet why, but the url could be something like this:
		// dial tcp: missing port in address [[::ffff:220.249.243.126]]:80
		// we just fix it here.
		url = strings.Replace(url, "[[", "[", 1)
		url = strings.Replace(url, "]]", "]", 1)
	}
	server, err := net.DialTimeout("tcp", url, time.Second*60)
	if err != nil {
		info("ERROR: cannot dial to server %s: %v", url, err)
		return
	}
	info("connected to server: %s", url)
	initServers(url, 0)

	defer func() {
		server.Close()
		deleteServers(url)
		debug("closed server")
	}()

	ch_local := make(chan []byte)
	ch_server := make(chan DataInfo)
	go readDataFromLocal(ch_local, local)
	go readDataFromServer(ch_server, server, url)

	shouldStop := false
	for {
		if shouldStop {
			break
		}

		select {
		case data, ok := <-ch_local:
			if !ok {
				shouldStop = true
				break
			}
			server.Write(data)
		case di, ok := <-ch_server:
			if !ok {
				shouldStop = true
				break
			}
			buffer = encrypt.Encrypt(di.data[:di.size], KEY)
			b := make([]byte, 2)
			binary.BigEndian.PutUint16(b, uint16(len(buffer)))
			local.Write(b)
			local.Write(buffer)
		case <-time.After(3600 * time.Second):
			debug("timeout on %s", url)
			shouldStop = true
			break
		}
	}
}

func readDataFromServer(ch chan DataInfo, conn net.Conn, url string) {
	debug("enter readDataFromServer")
	defer func() {
		debug("leave readDataFromServer")
	}()
	for {
		data := make([]byte, 7000+rand.Intn(2000))
		n, err := conn.Read(data)
		if err != nil {
			break
		}
		incrServers(url, int64(n))
		debug("data from server:\n%s", data[:n])
		ch <- DataInfo{data, n}
	}
	close(ch)
}

func readDataFromLocal(ch chan []byte, conn net.Conn) {
	debug("enter readDataFromLocal")
	defer func() {
		debug("leave readDataFromLocal")
	}()
	for {
		buffer := make([]byte, 2)
		_, err := io.ReadFull(conn, buffer)
		if err != nil {
			break
		}
		size := binary.BigEndian.Uint16(buffer)
		buffer = make([]byte, size)
		_, err = io.ReadFull(conn, buffer)
		if err != nil {
			break
		}
		data, err := encrypt.Decrypt(buffer, KEY)
		if err != nil {
			fmt.Printf("ERROR: cannot decrypt data from local.")
			break
		}
		debug("data from local:\n%s", data)
		ch <- data
	}
	close(ch)
}

func getKey() []byte {
	b := getGoixyConfig()
	if b == nil {
		fmt.Printf("Goixy Config not found")
		os.Exit(2)
	}
	err := json.Unmarshal(b, &GC)
	if err != nil {
		fmt.Printf("invalid json in Goixy Config: %v\n", err)
		os.Exit(2)
	}

	s := strings.TrimSpace(GC.Key)
	sum := sha256.Sum256([]byte(s))
	return sum[:]
}

func initServers(key string, bytes int64) {
	m := cmap.New()
	now := time.Now()
	m.Set("ts", now.Unix())
	m.Set("bytes", bytes)
	Servers.Set(key, m)
}

func incrServers(key string, n int64) {
	if m, ok := Servers.Get(key); ok {
		if tmp, ok := m.(cmap.ConcurrentMap).Get("bytes"); ok {
			m.(cmap.ConcurrentMap).Set("bytes", tmp.(int64)+n)
		}
	} else {
		initServers(key, n)
	}
}

func deleteServers(key string) {
	Servers.Remove(key)
}

func getGoixyConfig() []byte {
	usr, err := user.Current()
	if err != nil {
		fmt.Printf("user current: %v\n", err)
		os.Exit(2)
	}
	fileConfig := path.Join(usr.HomeDir, ".goixy/config.json")
	if _, err := os.Stat(fileConfig); os.IsNotExist(err) {
		fmt.Printf("config file is missing: %v\n", fileConfig)
		os.Exit(2)
	}

	data, err := ioutil.ReadFile(fileConfig)
	if err != nil {
		fmt.Printf("failed to load direct-servers file: %v\n", err)
		os.Exit(1)
	}
	return data
}

func info(format string, a ...interface{}) {
	ts := time.Now().Format("2006-01-02 15:04:05")
	prefix := fmt.Sprintf("[%s][%d] ", ts, countConnected)
	fmt.Printf(prefix+format+"\n", a...)
}

func debug(format string, a ...interface{}) {
	if DEBUG {
		info(format, a...)
	}
}

type DataInfo struct {
	data []byte
	size int
}
