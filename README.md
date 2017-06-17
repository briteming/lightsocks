# LightSocks

A Generic Secure Proxy Server.

Pair with [mitnk/goixy](https://github.com/mitnk/goixy)

## Install

```
$ go get github.com/mitnk/lightsocks
```

## Usage

```
$ lightsocks -host 0.0.0.0 -port 5678
[2017-06-17 11:06:54][0] lightsocks v1.6.1
[2017-06-17 11:06:54][0] listen on 0.0.0.0:5678
```

Note: for first time run, you need to generate a secret key:

```
# for example, you can generate this key with openssl
$ openssl rand -base64 32 > ~/.lightsockskey
$ cat ~/.lightsockskey
```

and share this key with goixy. But do not share this key with others.

also See `lightsocks -h` for help.
