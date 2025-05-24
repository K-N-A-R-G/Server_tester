# server.py

import asyncio
import select
import socket
import struct
import time

from types_common import NamedQueue, LogDict


srv_status: list[bool] = [True]

def server_sock() -> socket.socket:
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("localhost", 5959))
    srv.listen()
    print('serv_socket created')
    return srv


def accept_conn(
 sck: socket.socket,
 sockets: set[socket.socket],
 queue_: NamedQueue,
 clients_total: int,
 SERVER_TYPE: str,
 mode: str = 'blocking') -> None:
    try:
        conn, addr = sck.accept()
        if mode == 'unblocking':
            conn.setblocking(False)
        # print(f"Connection from {addr}")
        sockets.add(conn)
    except BlockingIOError:
        raise
    except OSError as ex:
        if is_server_crashed(ex) and srv_status[0]:
            print('\033[91mserver accept fatal error\033[0m')
            log_server_error(
             queue_, SERVER_TYPE, clients_total,
             'fatal_error', str(ex))
            srv_status[0] = False
        return None
    except socket.error as err:
        log_server_error(
         queue_, SERVER_TYPE, clients_total,
         'accept_connection', str(err))
    return None


def send_response(client_sock: socket.socket,
                  queue_: NamedQueue,
                  clients_total: int,
                  SERVER_TYPE: str) -> bool:
    try:
        data = client_sock.recv(1024)
        # print('received', data)
        if not data:
            return False
    except socket.error as err:
        if err.errno == 11:
            # print('send_response" ', err)
            return True
            # raise ConnectionError("Connection lost")
    try:
        now = time.time()
        mark = struct.unpack('!hd', data)[0]
        # print(f'{now = }')
        response = struct.pack('!hd', mark, now)
        # print(f'{struct.unpack("!hd", response) = }')
        client_sock.send(response)
    except socket.error as err:
        log_server_error(
         queue_, SERVER_TYPE, clients_total,
         'recv_send_error', str(err))
        client_sock.close()
        return False
    except Exception as ex:
        if is_server_crashed(ex):
            log_server_error(
             queue_, SERVER_TYPE, clients_total,
             'fatal_error', str(ex))
            srv_status[0] = False
            return False
        print(ex)
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
    que.put(log)


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
 srv: socket.socket, QUE: NamedQueue,
 SERVER_TYPE: str, total_clients_quantity: int) -> None:
    print(srv)

    def event_loop(
     server_socket: socket.socket,
     queue_: NamedQueue,
     clients_total: int) -> None:
        sockets = set()
        sockets.add(server_socket)
        while sockets and srv_status:
            # print(f'{len(sockets) = }')
            try:
                sockets_for_read, _, _ = select.select(sockets, [], [], 5)
                for sock in sockets_for_read:
                    if not srv_status:
                        break
                    if sock is server_socket:
                        accept_conn(sock, sockets, queue_,
                                     clients_total, SERVER_TYPE)
                    else:
                        if not send_response(
                         sock, queue_,
                         clients_total, SERVER_TYPE):
                            sockets.remove(sock)
                if not sockets_for_read:
                    print('No conection spotted')
                    server_socket.close()
                    sockets.remove(server_socket)
            except Exception as ex:
                if is_server_crashed(ex):
                    log_server_error(
                     queue_, SERVER_TYPE, clients_total,
                     'fatal_error', str(ex))
                    print('\033[31mSERVER CRASHED\033[0m')
                    srv_status[0] = False
                    break
                print(ex)
                log_server_error(
                 queue_, SERVER_TYPE,
                 clients_total, 'select_error', str(ex))
                break

    event_loop(srv, QUE, total_clients_quantity)
    srv.close()
    print('Server stopped')


def server_unblocked(
 srv: socket.socket,
 QUE: NamedQueue,
 SERVER_TYPE: str,
 total_clients_quantity: int) -> None:
    srv.setblocking(False)

    def event_loop(
     server_socket: socket.socket,
     queue_: NamedQueue,
     clients_total: int) -> None:
        sockets: set[socket.socket] = set()
        delay: int | float = 0

        while srv_status[0]:
            try:
                accept_conn(srv, sockets, queue_,
                            clients_total,
                            SERVER_TYPE, mode='unblocking')
                delay = 0
            except BlockingIOError:
                if not delay:
                    delay = time.time()
                if time.time() - delay >= 3:
                    print('No connection spotted')
                    server_socket.close()
                    break
            try:
                for sock in set(sockets):
                    if not send_response(
                     sock, queue_,
                     clients_total, SERVER_TYPE):
                        sockets.remove(sock)
            except Exception as ex:
                if is_server_crashed(ex):
                    log_server_error(
                     queue_, SERVER_TYPE, clients_total,
                     'fatal_error', str(ex))
                    print('\033[31mSERVER CRASHED\033[0m')
                    srv_status[0] = False
                    break
                # print(f'{SERVER_TYPE}:', ex)
                # log_server_error(
                 # queue_, SERVER_TYPE,
                 # clients_total, 'unblocked_error', str(ex))
                # break
                raise

    event_loop(srv, QUE, total_clients_quantity)
    srv.close()
    print('Server stopped')


def server_mixed(
    srv: socket.socket,
    QUE: NamedQueue,
    SERVER_TYPE: str,
    total_clients_quantity: int
) -> None:
    srv.setblocking(False)

    def event_loop(
        server_socket: socket.socket,
        queue_: NamedQueue,
        clients_total: int
    ) -> None:
        sockets: set[socket.socket] = set()
        delay: int | float = 0

        while srv_status[0]:
            try:
                accept_conn(server_socket, sockets, queue_,
                 clients_total, SERVER_TYPE)
                delay = 0
            except BlockingIOError:
                if not delay:
                    delay = time.time()
                if time.time() - delay >= 5:
                    print('No connection spotted')
                    server_socket.close()
                    break

                try:
                    # проверка готовности всех клиентских сокетов на чтение
                    sockets_for_read, _, _ = select.select(sockets, [], [], 0)
                except Exception as ex:
                    if is_server_crashed(ex):
                        log_server_error(
                            queue_, SERVER_TYPE, clients_total,
                            'fatal_error', str(ex))
                        print('\033[31mSERVER CRASHED\033[0m')
                        srv_status[0] = False
                        break
                    print(ex)
                    log_server_error(
                        queue_, SERVER_TYPE, clients_total,
                        'select_error', str(ex))
                    continue

                for sock in set(sockets_for_read):
                    if not send_response(sock, queue_,
                     clients_total, SERVER_TYPE):
                        sockets.remove(sock)
                        try:
                            sock.close()
                        except OSError:
                            pass

            except Exception as ex:
                if is_server_crashed(ex):
                    log_server_error(
                        queue_, SERVER_TYPE, clients_total,
                        'fatal_error', str(ex))
                    srv_status[0] = False
                    break
                print(ex)
                log_server_error(
                    queue_, SERVER_TYPE, clients_total,
                    'accept_error', str(ex))
                break

    event_loop(srv, QUE, total_clients_quantity)
    srv.close()
    print('Server stopped')


def server_async(
    _unused: None,
    QUE: NamedQueue,
    SERVER_TYPE: str,
    total_clients_quantity: int
) -> None:

    async def handle_client(reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                try:
                    data = await reader.read(1024)
                except asyncio.IncompleteReadError:
                    break  # клиент закрыл соединение нештатно
                except ConnectionResetError:
                    break  # клиент разорвал соединение
                except Exception as ex:
                    log_server_error(
                        QUE, SERVER_TYPE, total_clients_quantity,
                        'recv_error', str(ex))
                    break

                if not data:
                    break  # клиент закрыл соединение штатно

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
            srv_status[0] = False
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
                    srv_status[0] = False
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
                srv_status[0] = False

    runner()
    print('Server stopped')
    return None
