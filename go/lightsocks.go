package main

import (
	"fmt"
	"flag"
	"io"
	"io/ioutil"
	"net"
	"encoding/binary"
	"crypto/sha256"
	"os/user"
	"path"
	"strconv"
	"strings"
	"time"

	"github.com/mitnk/goutils/encrypt"
)

var remoteDebug = false
var countConnected = 0

func check(e error) {
    if e != nil {
        panic(e)
    }
}

type DataInfo struct {
	data []byte
	size int
}

func main() {
	port := flag.String("p", "3389", "port")
	debug := flag.Bool("v", false, "debug")
	flag.Usage = func() {
        fmt.Printf("lightsocks [flags]\nwhere flags are:\n")
        flag.PrintDefaults()
    }
    flag.Parse()
    fmt.Printf("lightsocks v0.10\n")

	remoteDebug = *debug
	remote, err := net.Listen("tcp", ":" + *port)
	check(err)
	defer remote.Close()
    fmt.Printf("listen on port %s\n", *port)

	for {
        local, err := remote.Accept()
        if err != nil {
			fmt.Printf("Error: %v\n", err)
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

	info("local connected: %v.", local.RemoteAddr())
	key := getKey()
	buffer := make([]byte, 1)
	_, err := io.ReadFull(local, buffer)
	if err != nil {
		fmt.Printf("cannot read size from local.\n")
		return
	}

	buffer = make([]byte, buffer[0])
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		fmt.Printf("cannot read host from local.\n")
		return
	}
	host, err := encrypt.Decrypt(buffer, key[:])
	if err != nil {
		fmt.Printf("ERROR: cannot decrypt host.\n")
		return
	}

	buffer = make([]byte, 2)
	_, err = io.ReadFull(local, buffer)
	if err != nil {
		fmt.Printf("cannot read port from local.\n")
		return
	}
	port := binary.BigEndian.Uint16(buffer)

	url := net.JoinHostPort(string(host), strconv.Itoa(int(port)))
	server, err := net.Dial("tcp", url)
	if err != nil {
		fmt.Printf("ERROR: cannot dial to server %s\n", url)
		return
	}
	info("connected to server: %s", url)
	defer server.Close()

	ch_local := make(chan []byte)
	ch_server := make(chan DataInfo)
	go readDataFromLocal(ch_local, ch_server, local, key[:])
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
			buffer = encrypt.Encrypt(di.data[:di.size], key[:])
			b := make([]byte, 2)
			binary.BigEndian.PutUint16(b, uint16(len(buffer)))
			local.Write(b)
			local.Write(buffer)
		}
	}
}

func readDataFromServer(ch chan DataInfo, conn net.Conn) {
	for {
		data := make([]byte, 8192)
		n, err := conn.Read(data)
		if err != nil {
			ch <- DataInfo{nil, 0}
			return
		}
		ch <- DataInfo{data, n}
	}
}

func readDataFromLocal(ch chan []byte, ch2 chan DataInfo, conn net.Conn, key []byte) {
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
		data, err := encrypt.Decrypt(buffer, key)
		if err != nil {
			fmt.Printf("ERROR: cannot decrypt data from local.")
			ch <- nil
			return
		}
		ch <- data
	}
}

func getKey() [32]byte {
	usr, err := user.Current()
	check(err)
	fileKey := path.Join(usr.HomeDir, ".lightsockskey")
	data, err := ioutil.ReadFile(fileKey)
	s := strings.TrimSpace(string(data))
	check(err)
	return sha256.Sum256([]byte(s))
}

func info(format string, a...interface{}) (n int, err error) {
	if !remoteDebug {
		return 0, nil
	}
	ts := time.Now().Format("2006-01-02 15:04:05")
	prefix := fmt.Sprintf("[%s][%d] ", ts, countConnected)
	return fmt.Printf(prefix + format + "\n", a...)
}
