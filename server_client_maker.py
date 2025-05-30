# server_client_maker.py

import random
import resource
import socket
import struct
import threading
import time

from collections.abc import Callable
from db_utils import init_db, send_to_base
from graph_matplotlib_tkinter import make_table
from server import server_sock, server_select, srv_status,\
 server_unblocked, server_mixed, server_async
from types_common import LogData, NamedQueue


soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))

address = ("localhost", 5959)
CNT = 2
# SERVER_TYPE = ''
que_first: NamedQueue = NamedQueue('que_first')
que_next: NamedQueue = NamedQueue('que_next')
# QUE = que_first


def client_sock(SERVER_TYPE: str,
 total_clients_quantity: int, QUE: NamedQueue) -> None:
    try:
        clt = socket.socket()
    except OSError as er:
        print(f"!!! UNCAUGHT OSError during client socket creation: {er}")
        return None

    cnt = 0
    attempts = 3000
    log_data: LogData = {
        'log_type': 'client',
        'server_type': SERVER_TYPE,
        'client_id': threading.current_thread().native_id,
        'clients_total': total_clients_quantity,
        'conn_attempt': None,
        't_send_attempt': None,
        'send_id': None,
        't_send_success': None,
        't_server_response': None,
        't_response': None,
        'error': ''
    }

    def clear_log(log_data: LogData) -> None:
        log_data.update(
            {
                'conn_attempt': None,
                't_send_attempt': None,
                'send_id': None,
                't_send_success': None,
                't_server_response': None,
                't_response': None,
                'error': '',
            }
        )

    while attempts:
        try:
            clt.connect(address)
            attempt_number = 3001 - attempts
            attempts = 3000
            break
        except Exception:
            time.sleep(.001)
            attempts -= 1
    else:
        log_data['error'] = 'Connection attempts is over'
        QUE.put(log_data)
        clt.close()
        return None

    try:
        while cnt < CNT:
            try:
                try:
                    clear_log(log_data)
                    data_float = random.random()
                    data_bytes: bytes = struct.pack('!hd', cnt, data_float)
                    log_data['conn_attempt'] = attempt_number
                    t_send_attempt = time.time()
                    log_data['send_id'] = cnt
                    log_data['t_send_attempt'] = round(t_send_attempt, 6)
                    clt.send(data_bytes)
                    # print('sended', data_bytes)
                    t_send_success = round(time.time() - t_send_attempt, 6)
                    log_data['t_send_success'] = t_send_success
                    t_recv: bytes = clt.recv(1024)
                    # print('client:', t_recv)
                    t_server_response: float = struct.unpack('!hd', t_recv)[1]
                    log_data['t_server_response'] = round(t_server_response, 6)
                    t_response: float = round(time.time() - t_server_response, 6)
                    log_data['t_response'] = t_response
                except Exception as ex:
                    log_data['error'] = ex.args[1]\
                     if len(ex.args) > 1 else str(ex)
                finally:
                    cnt += 1
                    QUE.put(log_data.copy())
            except OSError as ex:
                print(f"!!! UNCAUGHT OSError in exchange cycle: {ex}")
                break
    finally:
        try:
            clt.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            clt.close()
        except OSError:
            pass


def run_test_suite() -> None:
    while True:
        db_option = input('''
        Do you want to keep the existing database data? (y/n)
         ''')
        if db_option in 'Yy':
            db_erase = False
            break
        elif db_option in'Nn':
            db_erase = True
            break
        time.sleep(0.1)

    init_db(new=db_erase)

    ServerFunc = Callable[[socket.socket, NamedQueue, str, int], None]
    server_options: dict[str, tuple[str, ServerFunc]] = {
     '1': ('server_select', server_select),
     '2': ('server_unblocked', server_unblocked),
     '3': ('server_mixed', server_mixed),
     '4': ('server_async', server_async)
    }

    start_message = '''
    Choose server type:
    1 - select.select
    2 - socket.unblocked
    3 - mixed server using select() for blocking client`s connections
    4 - server on asyncio
    q - exit program
     '''

    while True:
        option = input(start_message)
        if option in server_options:
            set_option = server_options.get(option)
            SERVER_TYPE = set_option[0]
            break
        elif option == 'q':
            exit()
        time.sleep(0.1)

    for total_clients_quantity in range(64, 4097, 64):
        print(f'\n{srv_status = }')
        if not srv_status[0]:
            break
        print(f'\n{total_clients_quantity} clients\n')
        QUE = (que_next, que_first)[bool(total_clients_quantity % 128)]
        if set_option[0] == 'server_async':
            srv = None
        else:
            srv = server_sock()
        thr_srv = threading.Thread(target=set_option[1],
                                   args=(srv, QUE, SERVER_TYPE,
                                         total_clients_quantity))
        thr_srv.start()
        clts = []
        for _ in range(total_clients_quantity):
            clts.append(threading.Thread(target=client_sock,
             args=(SERVER_TYPE, total_clients_quantity, QUE)))
        print(f'made {len(clts)}')
        print('start')
        for x in clts:
            x.start()
        for x in clts:
            x.join()
        thr_srv.join()

        QUE.put('End')  # type: ignore
        thr_send = threading.Thread(target=send_to_base, args=(QUE,))
        thr_send.start()

    thr_send.join(5)
    return None

if __name__ == '__main__':
    run_test_suite()
    make_table()
