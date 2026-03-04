# server.py

import asyncio
import resource
import select
import socket
import struct
import time

from db_utils import send_to_base
from multiprocessing.sharedctypes import Synchronized
from types_common import NamedQueue, LogDict


soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))


class ClientConnection:
    __slots__ = ('sock', 'pocket', '_hash')

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.pocket = bytearray()
        self._hash = hash(sock)

    def __hash__(self): return self._hash

    def __eq__(self, other):
        return isinstance(other, ClientConnection) and self.sock is other.sock

    def fileno(self):
        return self.sock.fileno()

    def close(self):
        try:
            self.sock.close()
        finally:
            self.pocket.clear()


def server_sock() -> socket.socket:
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("localhost", 5959))
    srv.listen()
    print('serv_socket created')
    return srv


def accept_conn(
 sck: socket.socket,
 sockets: set[ClientConnection],
 queue_: NamedQueue,
 clients_total: int,
 SERVER_TYPE: str,
 srv_status: Synchronized,
 mode: str = 'blocking') -> None:
    try:
        conn, addr = sck.accept()

        if mode == 'unblocking':
            conn.setblocking(False)

        # Package the socket into a ClientConnection object right here.
        # This ensures that a "unit" enters the set with a buffer ready.
        new_client = ClientConnection(conn)
        sockets.add(new_client)

    except BlockingIOError:
        raise
    except OSError as ex:
        if is_server_crashed(ex) and srv_status.value:
            print('\033[91mserver accept fatal error\033[0m')
            log_server_error(
             queue_, SERVER_TYPE, clients_total,
             'fatal_error', str(ex))
            srv_status.value = False
        return None
    except socket.error as err:
        log_server_error(
         queue_, SERVER_TYPE, clients_total,
         'accept_connection', str(err))
    return None


def send_response(conn: ClientConnection,
                  queue_: NamedQueue,
                  clients_total: int,
                  SERVER_TYPE: str,
                  srv_status: Synchronized) -> bool:
    # 1. IO Section (Reading)
    try:
        data = conn.sock.recv(1024)
        if not data:
            return False
        conn.pocket.extend(data)
    except socket.error as err:
        if err.errno == 11: # EAGAIN
            return True
        log_server_error(queue_, SERVER_TYPE, clients_total, 'recv_error', str(err))
        return False

    # 2. Control Section (Completeness of Message)
    if len(conn.pocket) < 10:
        return True

    # 3. Logic and Response Section (Processor + Write)
    try:
        # Extract the packet atomically
        raw_packet = conn.pocket[:10]
        del conn.pocket[:10]

        mark = struct.unpack('!hd', raw_packet)[0]
        response = struct.pack('!hd', mark, time.time())

        # Forwarding 10 bytes at once will not block the thread
        conn.sock.sendall(response)

    except Exception as ex:
        if is_server_crashed(ex):
            log_server_error(queue_, SERVER_TYPE, clients_total, 'fatal_error', str(ex))
            srv_status.value = False
        return False

    return True


def log_server_error(que: NamedQueue,
                     SERVER_TYPE: str,
                     clients_total: int,
                     error_type: str,
                     message: str) -> None:
    log: LogDict = {
        'log_type': 'server',
        'server_type': SERVER_TYPE,
        'clients_total': clients_total,
        'error_type': error_type,
        'message': message,
        'timestamp': round(time.time(), 6)
    }
    send_to_base(log)


CRITICAL_SERVER_ERRNOS = {
}

def is_server_crashed(ex: BaseException) -> bool:
    # 24 - EMFILE — Too many open files
    # 23 - ENFILE — File table overflow
    # 99 - EADDRNOTAVAIL — Cannot assign requested address
    # 105 - ENOBUFS — No buffer space available
    return any([
        isinstance(ex, OSError) and ex.errno in\
         (23, 24, 99, 105),
        'filedescriptor out of range' in str(ex),       # select() limit
        'no file descriptors' in str(ex).lower()
    ])



def server_select(
 QUE: NamedQueue,
 SERVER_TYPE: str,
 total_clients_quantity: int,
 srv_status: Synchronized) -> None:
    srv = server_sock()
    print(srv)
    sockets = set((srv,))
    while sockets and srv_status.value:
        # print(f'{len(sockets) = }')
        try:
            sockets_for_read, _, _ = select.select(sockets, [], [], 5)
            for sock in sockets_for_read:
                if not srv_status.value:
                    break
                if sock is srv:
                    accept_conn(sock, sockets, QUE,
                                 total_clients_quantity, SERVER_TYPE,
                                 srv_status)
                else:
                    if not send_response(
                     sock, QUE,
                     total_clients_quantity, SERVER_TYPE, srv_status):
                        sockets.remove(sock)
            if not sockets_for_read:
                print('No conection spotted')
                srv.close()
                sockets.remove(srv)
        except Exception as ex:
            if is_server_crashed(ex):
                log_server_error(
                 QUE, SERVER_TYPE, total_clients_quantity,
                 'fatal_error', str(ex))
                print('\033[31mSERVER CRASHED\033[0m')
                srv_status.value = False
                break
            print(ex)
            log_server_error(
             QUE, SERVER_TYPE,
             total_clients_quantity, 'select_error', str(ex))
            break

    srv.close()
    print('Server stopped')


def server_unblocked(
 QUE: NamedQueue,
 SERVER_TYPE: str,
 total_clients_quantity: int,
 srv_status: Synchronized) -> None:
    srv = server_sock()
    srv.setblocking(False)
    connections: set[ClientConnection] = set()
    delay: float = 0

    while srv_status.value:
        try:
            accept_conn(srv, connections, QUE,
                        total_clients_quantity,
                        SERVER_TYPE, srv_status, mode='unblocking')
            delay = 0
        except BlockingIOError:
            if not delay:
                delay = time.time()
            if time.time() - delay >= 3:
                print('No connection spotted')
                srv.close()
                break
        try:
            for sock in set(connections):
                if not send_response(
                 sock, QUE,
                 total_clients_quantity, SERVER_TYPE, srv_status):
                    connections.remove(sock)
        except Exception as ex:
            if is_server_crashed(ex):
                log_server_error(
                 QUE, SERVER_TYPE, total_clients_quantity,
                 'fatal_error', str(ex))
                print('\033[31mSERVER CRASHED\033[0m')
                srv_status.value = False
                break
            raise
        time.sleep(0)

    srv.close()
    print('Server stopped')


def server_mixed(
    QUE: NamedQueue,
    SERVER_TYPE: str,
    total_clients_quantity: int,
    srv_status: Synchronized
) -> None:
    srv = server_sock()
    srv.setblocking(False)

    sockets: set[socket.socket] = set()
    delay: int | float = 0

    while srv_status.value:
        try:
            accept_conn(srv, sockets, QUE,
             total_clients_quantity, SERVER_TYPE, srv_status)
            delay = 0
        except BlockingIOError:
            if not delay:
                delay = time.time()
            if time.time() - delay >= 5:
                print('No connection spotted')
                srv.close()
                break

            try:
                sockets_for_read, _, _ = select.select(sockets, [], [], 0)
            except Exception as ex:
                if is_server_crashed(ex):
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'fatal_error', str(ex))
                    print('\033[31mSERVER CRASHED\033[0m')
                    srv_status.value = False
                    break
                print(ex)
                log_server_error(
                    QUE, SERVER_TYPE, total_clients_quantity,
                    'select_error', str(ex))
                continue

            for sock in set(sockets_for_read):
                if not send_response(sock, QUE,
                 total_clients_quantity, SERVER_TYPE, srv_status):
                    sockets.remove(sock)
                    try:
                        sock.close()
                    except OSError:
                        pass

        except Exception as ex:
            if is_server_crashed(ex):
                log_server_error(
                    QUE, SERVER_TYPE, total_clients_quantity,
                    'fatal_error', str(ex))
                srv_status.value = False
                break
            print(ex)
            log_server_error(
                QUE, SERVER_TYPE, total_clients_quantity,
                'accept_error', str(ex))
            break

    srv.close()
    print('Server stopped')


def server_async(
    QUE: NamedQueue,
    SERVER_TYPE: str,
    total_clients_quantity: int,
    srv_status: Synchronized
) -> None:

    async def handle_client(reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                try:
                    data = await reader.read(1024)
                except asyncio.IncompleteReadError:
                    break  # the client closed the connection abnormally
                except ConnectionResetError:
                    break  # The client has disconnected
                except Exception as ex:
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'recv_error', str(ex))
                    break

                if not data:
                    break  # the client closed the connection normally

                try:
                    now = time.time()
                    mark = struct.unpack('!hd', data)[0]
                    response = struct.pack('!hd', mark, now)
                    writer.write(response)
                    await writer.drain()
                except Exception as ex:
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'send_error', str(ex))
                    break

        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def async_main() -> None:
        try:
            server = await asyncio.start_server(
                handle_client, host='localhost', port=5959)
        except Exception as ex:
            log_server_error(
                QUE, SERVER_TYPE, total_clients_quantity,
                'start_server_error', str(ex))
            srv_status.value = False
            return None

        async with server:
            try:
                await asyncio.wait_for(server.serve_forever(), timeout=5.0)
            except asyncio.TimeoutError:
                print('No connection spotted (timeout)')
            except Exception as ex:
                if is_server_crashed(ex):
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'fatal_error', str(ex))
                    srv_status.value = False
                else:
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'serve_forever_error', str(ex))

    def runner() -> None:
        try:
            asyncio.run(async_main())
        except Exception as ex:
            log_server_error(
                QUE, SERVER_TYPE, total_clients_quantity,
                'event_loop_crash', str(ex))
            if is_server_crashed(ex):
                print('\033[31mSERVER CRASHED\033[0m')
                srv_status.value = False

    runner()
    print('Server stopped')
    return None
