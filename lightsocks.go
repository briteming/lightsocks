package main

import (
	"crypto/sha256"
	"encoding/binary"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"math/rand"
	"net"
	"os/user"
	"path"
	"reflect"
	"strconv"
	"strings"
	"time"

	"github.com/mitnk/goutils/encrypt"
)

var VERSION = "1.2.0"
var countConnected = 0
var KEY = getKey()

func main() {
	port := flag.String("p", "12345", "port")
	flag.Usage = func() {
		fmt.Printf("Usage of lightsocks v%s:\n", VERSION)
		fmt.Printf("lightsocks [flags]\n")
		flag.PrintDefaults()
	}
	flag.Parse()
	remote, err := net.Listen("tcp", ":"+*port)
	check(err)
	defer remote.Close()
	info("lightsocks v%s", VERSION)
	info("listen on port %s", *port)

	for {
		local, err := remote.Accept()
		if err != nil {
			info("error when accept: %v", err)
			continue
		}
		go handleClient(local)
	}
}

func handleClient(local net.Conn) {
	defer local.Close()
	countConnected += 1
	defer func() {
		countConnected -= 1
	}()

	info("local connected: %v", local.RemoteAddr())
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
	if err != nil || !reflect.DeepEqual(KEY[8:16], dataCheck) {
		info("invalid local")
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
	server, err := net.Dial("tcp", url)
	if err != nil {
		info("ERROR: cannot dial to server %s", url)
		return
	}
	info("connected to server: %s", url)
	defer server.Close()

	ch_local := make(chan []byte)
	ch_server := make(chan DataInfo)
	go readDataFromLocal(ch_local, ch_server, local)
	go readDataFromServer(ch_server, server)

	shouldStop := false
	for {
		if shouldStop {
			break
		}

		select {
		case data := <-ch_local:
			if data == nil {
				local.Close()
				info("local closed %v", local.RemoteAddr())
				shouldStop = true
				break
			}
			server.Write(data)
		case di := <-ch_server:
			if di.data == nil {
				server.Close()
				info("server closed %v", server.RemoteAddr())
				break
			}
			buffer = encrypt.Encrypt(di.data[:di.size], KEY)
			b := make([]byte, 2)
			binary.BigEndian.PutUint16(b, uint16(len(buffer)))
			local.Write(b)
			local.Write(buffer)
		}
	}
}

func readDataFromServer(ch chan DataInfo, conn net.Conn) {
	for {
		data := make([]byte, 7000+rand.Intn(2000))
		n, err := conn.Read(data)
		if err != nil {
			ch <- DataInfo{nil, 0}
			return
		}
		ch <- DataInfo{data, n}
	}
}

func readDataFromLocal(ch chan []byte, ch2 chan DataInfo, conn net.Conn) {
	for {
		buffer := make([]byte, 2)
		_, err := io.ReadFull(conn, buffer)
		if err != nil {
			ch <- nil
			ch2 <- DataInfo{nil, 0}
			return
		}
		size := binary.BigEndian.Uint16(buffer)
		buffer = make([]byte, size)
		_, err = io.ReadFull(conn, buffer)
		if err != nil {
			ch <- nil
			return
		}
		data, err := encrypt.Decrypt(buffer, KEY)
		if err != nil {
			fmt.Printf("ERROR: cannot decrypt data from local.")
			ch <- nil
			return
		}
		ch <- data
	}
}

func getKey() []byte {
	usr, err := user.Current()
	check(err)
	fileKey := path.Join(usr.HomeDir, ".lightsockskey")
	data, err := ioutil.ReadFile(fileKey)
	s := strings.TrimSpace(string(data))
	check(err)
	sum := sha256.Sum256([]byte(s))
	return sum[:]
}

func info(format string, a ...interface{}) {
	ts := time.Now().Format("2006-01-02 15:04:05")
	prefix := fmt.Sprintf("[%s][%d] ", ts, countConnected)
	fmt.Printf(prefix+format+"\n", a...)
}

func check(e error) {
	if e != nil {
		panic(e)
	}
}

type DataInfo struct {
	data []byte
	size int
}
