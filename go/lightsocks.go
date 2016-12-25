package main

import (
	"fmt"
	"flag"
	_ "bufio"
	"io"
	"net"
	_ "os"
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

	buffer := make([]byte, 1)
	n, err := io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read size from client.")
		return
	}
	fmt.Printf("size: read %d bytes from client %v\n", n, buffer)

	buffer = make([]byte, buffer[0])
	n, err = io.ReadFull(client, buffer)
	if err != nil {
		fmt.Printf("cannot read url from client.")
		return
	}
	url, err := encrypt.Decrypt(buffer, key)
	check(err)
	fmt.Printf("url: %s\n", url)

	buf_port := make([]byte, 2)
	n, err = io.ReadFull(client, buf_port)
	if err != nil {
		fmt.Printf("cannot read port from client.")
		return
	}
	fmt.Printf("port: read %d bytes from client %v\n", n, buf_port)

	remote, err := net.Dial("tcp", string(buf_url) + string(port))
	check(err)

	ch_client := make(chan DataInfo)
	ch_remote := make(chan DataInfo)
	go readDataFromConn(ch_client, client)
	go readDataFromConn(ch_remote, remote)

	for {
		select {
		case di := <-ch_client:
			fmt.Printf("read %d bytes from client\n", di.size)
			remote.Write(di.data[:di.size])
		case di := <-ch_remote:
			fmt.Printf("read %d bytes from remote\n", di.size)
			client.Write(di.data[:di.size])
		}
	}
}

func readDataFromConn(ch chan DataInfo, conn net.Conn) {
	data := make([]byte, 8192)
	n, err := conn.Read(data)
	if err != nil {
		return
	}
	ch <- DataInfo{data, n}
}
