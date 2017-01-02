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
	server, err := net.Listen("tcp", ":" + *port)
	check(err)
	defer server.Close()
    fmt.Printf("listen on port %s\n", *port)

	for {
        client, err := server.Accept()
        if err != nil {
            continue
        }
        go handleClient(client)
    }
}

func handleClient(client net.Conn) {
    defer client.Close()
	countConnected += 1
    defer func() {
		countConnected -= 1
	}()

	info("connected from %v.", client.RemoteAddr())
	key := getKey()
	buffer := make([]byte, 1)
	_, err := io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read size from client.\n")
		return
	}

	buffer = make([]byte, buffer[0])
	_, err = io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read host from client.\n")
		return
	}
	host, err := encrypt.Decrypt(buffer, key[:])
	if err != nil {
		fmt.Printf("ERROR: cannot decrypt host.\n")
		return
	}

	buffer = make([]byte, 2)
	_, err = io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read port from client.\n")
		return
	}
	port := binary.BigEndian.Uint16(buffer)

	url := net.JoinHostPort(string(host), strconv.Itoa(int(port)))
	// fmt.Printf("url: %s\n", url)
	remote, err := net.Dial("tcp", url)
	if err != nil {
		fmt.Printf("ERROR: cannot dial to %s\n", url)
		return
	}
	info("connected to %s", url)
	defer remote.Close()

	ch_client := make(chan []byte)
	ch_remote := make(chan DataInfo)
	go readDataFromClient(ch_client, ch_remote, client, key[:])
	go readDataFromRemote(ch_remote, remote)

	shouldStop := false
	for {
		if shouldStop {
			break
		}

		select {
		case data := <-ch_client:
			if data == nil {
				client.Close()
				info("disconnected from local %v.", client.RemoteAddr())
				shouldStop = true
				break
			}
			remote.Write(data)
		case di := <-ch_remote:
			if di.data == nil {
				remote.Close()
				info("disconnected from remote %v.", remote.RemoteAddr())
				break
			}
			buffer = encrypt.Encrypt(di.data[:di.size], key[:])
			b := make([]byte, 2)
			binary.BigEndian.PutUint16(b, uint16(len(buffer)))
			client.Write(b)
			client.Write(buffer)
		}
	}
}

func readDataFromRemote(ch chan DataInfo, conn net.Conn) {
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

func readDataFromClient(ch chan []byte, ch2 chan DataInfo, conn net.Conn, key []byte) {
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
			fmt.Printf("ERROR: cannot decrypt data from client.")
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
	prefix := fmt.Sprintf("[%d] ", countConnected)
	return fmt.Printf(prefix + format + "\n", a...)
}
