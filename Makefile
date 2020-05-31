build:
	go get -u github.com/mitnk/goutils/encrypt
	go get -u github.com/orcaman/concurrent-map
	go build -o lightsocks .

all:
	GOOS=darwin GOARCH=amd64 go build -ldflags "-s -w" -o lightsocks-mac
	GOOS=windows GOARCH=386 go build -ldflags "-s -w" -o lightsocks32.exe
	GOOS=windows GOARCH=amd64 go build -ldflags "-s -w" -o lightsocks64.exe
	GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o lightsocks-linux-64
	GOOS=linux GOARCH=arm go build -ldflags "-s -w" -o lightsocks-arm-32
	GOOS=linux GOARCH=arm64 go build -ldflags "-s -w" -o lightsocks-arm-64

install:
	go get -u github.com/mitnk/goutils/encrypt
	go get -u github.com/orcaman/concurrent-map
	go build -ldflags "-s -w" -o lightsocks && cp lightsocks /usr/local/bin/

clean:
	rm -f lightsocks lightsocks-* *.exe
