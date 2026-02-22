"""
Minimal gRPC-like RPC transport:
  - Protobuf serialization (google-protobuf, compatible with v3, v4, v5+)
  - Length-prefixed binary framing over raw TCP
    (mirrors gRPC data frames; HTTP/2 layer omitted – grpcio unavailable)

Wire format:  [4B method_len][method][4B body_len][protobuf body]
"""

import socket, struct, threading
from google.protobuf import descriptor_pb2
from google.protobuf.descriptor_pool import DescriptorPool

# ── Build FileDescriptorProto ─────────────────────────────────────────────────
_pf = descriptor_pb2.FileDescriptorProto()
_pf.name    = "logging.proto"
_pf.package = "logging"
_pf.syntax  = "proto3"

_S = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
_O = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

def _msg(name, *fields):
    m = _pf.message_type.add()
    m.name = name
    for num, fname in fields:
        f = m.field.add()
        f.name = fname; f.number = num; f.type = _S; f.label = _O

_msg("LogRequest",  (1, "uuid"), (2, "msg"))
_msg("LogResponse", (1, "status"), (2, "uuid"))
_msg("GetRequest")
_msg("GetResponse", (1, "messages"))

_pool = DescriptorPool()
_pool.Add(_pf)

# ── Compatible class factory (works with protobuf 3.x, 4.x, 5.x, 6.x) ────────
def _get_class(name):
    descriptor = _pool.FindMessageTypeByName(f"logging.{name}")
    # protobuf >= 4.21 (v4+): use message_factory.GetMessageClass
    try:
        from google.protobuf import message_factory as _mf
        return _mf.GetMessageClass(descriptor)
    except AttributeError:
        pass
    # protobuf 3.x: use MessageFactory().GetPrototype
    try:
        from google.protobuf.message_factory import MessageFactory
        return MessageFactory().GetPrototype(descriptor)
    except Exception:
        pass
    # last resort: symbol_database
    from google.protobuf import symbol_database
    return symbol_database.Default().GetPrototype(descriptor)

LogRequest  = _get_class("LogRequest")
LogResponse = _get_class("LogResponse")
GetRequest  = _get_class("GetRequest")
GetResponse = _get_class("GetResponse")

# ── Wire framing ──────────────────────────────────────────────────────────────
def _send(sock, method, body):
    mb = method.encode()
    sock.sendall(struct.pack(">I", len(mb)) + mb +
                 struct.pack(">I", len(body)) + body)

def _recv_n(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            raise ConnectionError("Connection closed")
        buf += c
    return buf

def _recv(sock):
    ml     = struct.unpack(">I", _recv_n(sock, 4))[0]
    method = _recv_n(sock, ml).decode()
    bl     = struct.unpack(">I", _recv_n(sock, 4))[0]
    body   = _recv_n(sock, bl)
    return method, body

# ── Server ────────────────────────────────────────────────────────────────────
class RpcServer:
    def __init__(self, host, port):
        self.host = host; self.port = port; self._h = {}

    def register(self, method, handler):
        self._h[method] = handler

    def serve(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(10)
        print(f"[gRPC SERVER] Listening on {self.host}:{self.port}")
        while True:
            try:
                conn, addr = s.accept()
                threading.Thread(target=self._handle,
                                 args=(conn,), daemon=True).start()
            except OSError:
                break

    def _handle(self, conn):
        try:
            while True:
                method, body = _recv(conn)
                h = self._h.get(method)
                _send(conn, method, h(body) if h else b"")
        except (ConnectionError, struct.error, OSError):
            pass
        finally:
            conn.close()

# ── Client ────────────────────────────────────────────────────────────────────
class RpcClient:
    def __init__(self, host, port, timeout=3.0):
        self.host = host; self.port = port; self.timeout = timeout

    def call(self, method, body):
        with socket.create_connection((self.host, self.port),
                                      timeout=self.timeout) as s:
            _send(s, method, body)
            _, resp = _recv(s)
            return resp