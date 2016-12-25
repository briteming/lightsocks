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
	flag.Usage = func() {
        fmt.Printf("lightsocks [flags]\nwhere flags are:\n")
        flag.PrintDefaults()
    }
    flag.Parse()
    fmt.Printf("lightsocks v0.10\n")

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

	key := getKey()
	buffer := make([]byte, 1)
	_, err := io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read size from client.")
		return
	}

	buffer = make([]byte, buffer[0])
	_, err = io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read host from client.")
		return
	}
	host, err := encrypt.Decrypt(buffer, key[:])
	check(err)

	buffer = make([]byte, 2)
	_, err = io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read port from client.")
		return
	}
	port := binary.BigEndian.Uint16(buffer)

	url := net.JoinHostPort(string(host), strconv.Itoa(int(port)))
	// fmt.Printf("url: %s\n", url)
	remote, err := net.Dial("tcp", url)
	check(err)

	ch_client := make(chan []byte)
	ch_remote := make(chan DataInfo)
	go readDataFromClient(ch_client, client, key[:])
	go readDataFromRemote(ch_remote, remote)

	for {
		select {
		case data := <-ch_client:
			if data == nil {
				client.Close()
				break
			}
			remote.Write(data)
		case di := <-ch_remote:
			if di.data == nil {
				remote.Close()
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

func readDataFromClient(ch chan []byte, conn net.Conn, key []byte) {
	for {
		buffer := make([]byte, 2)
		_, err := io.ReadFull(conn, buffer)
		if err != nil {
			ch <- nil
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
		check(err)
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
