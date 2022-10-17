# coding:utf8
import json
import struct
import base64
import hashlib
from _thread import allocate_lock
from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol


connections = {}


class LegacyWebSocket(Protocol):
    def __init__(self, sockets):
        self.sockets = sockets
        self.user = {}
        self.lock = allocate_lock()

    def connectionMade(self):
        if self not in self.sockets:
            self.sockets[self] = {}
        self.transport.setTcpNoDelay(True)

    def dataReceived(self, msg):
        global connections
        print("**MESSAGE:", msg)
        
        if msg.lower().find(b'upgrade: websocket') != -1:
            self.hand_shake(msg)
        else:
            for i_msg in msg.split(b'\xff'):
                if not i_msg:
                    continue
                elif i_msg[0] == ord(b'\x00'):
                    i_msg = i_msg[1:]
                
                if i_msg.startswith(b'{'):
                    command = json.loads(i_msg.decode('utf-8'))
                    from_client_queue.put(command)
                else:
                    print("CALLING FIRST TIME LOOP", i_msg)
                    reactor.callLater(0.05, self.loop)
    
    def loop(self):
        if not queue.empty():
            i_data = queue.get()
            try:
                self.send_data(json.dumps(i_data, ensure_ascii=True).encode('ascii'))
            except KeyError:
                queue.put(i_data)
                raise
        reactor.callLater(0.05, self.loop)

    def connectionLost(self, reason):
        if self in self.sockets:
            del self.sockets[self]

    def generate_token(self, key1, key2, key3):
        key1 = key1.decode('ascii')
        key2 = key2.decode('ascii')
        
        num1 = int("".join([digit for digit in key1 if digit in '0123456789']))
        spaces1 = key1.count(" ")
        num2 = int("".join([digit for digit in key2 if digit in '0123456789']))
        spaces2 = key2.count(" ")
        
        assert num1 % key1.count(' ') == 0
        assert num2 % key2.count(' ') == 0
        
        #print("gen token:", num1, num2, spaces1, spaces2)

        combined = struct.pack(">II8s", num1 // spaces1, num2 // spaces2, key3)
        return hashlib.md5(combined).digest()

    def generate_token_2(self, key):
        key = key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        ser_key = hashlib.sha1(key).digest()
        return base64.b64encode(ser_key)

    def send_data(self, raw_str):
        #print("sending:", self)
        with self.lock:
            if self.sockets[self]['new_version']:
                back_str = []
                back_str.append(b'\x81')
                data_length = len(raw_str)

                if data_length <= 125:
                    back_str.append(bytes([data_length]))
                else:
                    back_str.append(bytes([126]))
                    back_str.append(bytes([data_length >> 8]))
                    back_str.append(bytes([data_length & 0xFF]))

                back_str = b"".join(back_str) + raw_str

                self.transport.write(back_str)
            else:
                back_str = b'\x00%s\xFF' % (raw_str)
                self.transport.write(back_str)
        #print("sent:", self)

    def parse_recv_data(self, msg):
        raw_str = ''
        #print("data length:", len(msg))
        #print("msg[0]:", ord(msg[0]))
        #print("msg[1]:", ord(msg[1]))
        if self.sockets[self]['new_version']:
            code_length = ord(msg[1]) & 127
            if code_length == 126:
                masks = msg[4:8]
                data = msg[8:]
            elif code_length == 127:
                masks = msg[10:14]
                data = msg[14:]
            else:
                masks = msg[2:6]
                data = msg[6:]

            i = 0
            for d in data:
                raw_str += chr(ord(d) ^ ord(masks[i % 4]))
                i += 1
        else:
            raw_str = msg.split("\xFF")[0][1:]

        return raw_str

    def hand_shake(self, msg):
        headers = {}
        header, data = msg.split(b'\r\n\r\n', 1)
        for line in header.split(b'\r\n')[1:]:
            key, value = line.split(b": ", 1)
            headers[key] = value

        headers[b"Location"] = b"ws://%s%s" % (headers[b"Host"], msg.split()[1])

        if b'Sec-WebSocket-Key1' in headers:
            key1 = headers[b"Sec-WebSocket-Key1"]
            key2 = headers[b"Sec-WebSocket-Key2"]
            key3 = data[:8]
            #print("generating token:", key1, '\n', key2, '\n', key3, '\n', msg)

            token = self.generate_token(key1, key2, key3)

            handshake = b'HTTP/1.1 101 Web Socket Protocol Handshake\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
Sec-WebSocket-Origin: %s\r\n\
Sec-WebSocket-Location: %s\r\n\r\n' % (headers[b'Origin'], headers[b'Location'])

            print('writing handshake:', handshake + token)
            self.transport.write(handshake + token)

            self.sockets[self]['new_version'] = False
        else:
            key = headers[b'Sec-WebSocket-Key']
            token = self.generate_token_2(key)

            handshake = b'HTTP/1.1 101 Switching Protocols\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
Sec-WebSocket-Accept: %s\r\n\r\n' % (token)
            print('writing handshake:', handshake)
            self.transport.write(handshake)

            self.sockets[self]['new_version'] = True


class WebSocketFactory(Factory):
    def __init__(self):
        self.sockets = {}

    def buildProtocol(self, addr):
        return LegacyWebSocket(self.sockets)


def main(_queue, _from_client_queue):
    global queue, from_client_queue
    queue = _queue
    from_client_queue = _from_client_queue
    port = 8080
    reactor.listenTCP(port, WebSocketFactory())
    print("listen", '192.168.1.196:' + str(port))
    reactor.run(installSignalHandlers=False)


