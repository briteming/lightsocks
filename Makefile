build:
	go build -o lightsocks .

install:
	go build -ldflags "-s -w" -o lightsocks && cp lightsocks /usr/local/bin/
