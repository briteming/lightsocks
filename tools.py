def u16_to_bytes(n):
    return n.to_bytes(2, 'big')


def bytes_to_int(s):
    return int.from_bytes(s, 'big')


def safe_recv(sock, size):
    data = sock.recv(size)
    if not data:
        return None

    size_left = size - len(data)
    while size_left > 0:
        _data = sock.recv(size_left)
        if not _data:
            return None
        data += _data
        size_left = size_left - len(_data)
    return data
