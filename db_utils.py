# db_utils.py

import re
import sqlite3

from query_loader import get_query
from typing import Any
from types_common import NamedQueue, LogData, ServerLogData


DB_NAME = "statistics.sqlite"


def init_db(DB_NAME: str=DB_NAME, new: bool=False) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        #  Режим журнала Write-Ahead Logging (WAL) в SQLite:
        #  Повышенная конкурентность;
        #  Более быстрая запись;
        #  Меньшее количество fsync();
        #  Автоматический чекпойнт (checkpoint)
        #  Устанавливать сразу же после соединения с базой
        cur.execute("PRAGMA journal_mode=WAL;")
        if new:
            cur.execute("DROP TABLE IF EXISTS test;")
            cur.execute("DROP TABLE IF EXISTS server_log;")
        cur.execute(
         "CREATE TABLE IF NOT EXISTS test ("
         "id INTEGER PRIMARY KEY,"
         "server_type TEXT,"
         "clients_total INTEGER,"
         "client_id INTEGER,"
         "conn_attempt INTEGER,"
         "send_id INTEGER,"
         "t_send_attempt REAL,"
         "t_send_success REAL,"  # time.time() - t_send_attempt
         "t_server_response REAL,"
         "t_response REAL,"  # time.time() - t_server_response
         "error TEXT"
         ");"
         )

        cur.execute(
         "CREATE TABLE IF NOT EXISTS server_log ("
         "id INTEGER PRIMARY KEY,"
         "server_type TEXT,"
         "clients_total INTEGER,"
         "error_type TEXT,"
         "message TEXT,"
         "timestamp REAL"
         ");"
         )

        conn.commit()


def send_to_base(
 que: NamedQueue, db_name: str=DB_NAME) -> None:
    with sqlite3.connect(db_name) as conn:
        cur = conn.cursor()
        print(que.name, f'connected, ({que.qsize()} elements)')
        try:
            while (row := que.get(timeout=1)) != 'End':  # type: ignore
                # print('sending', que.qsize())

                if row['log_type'] == 'server':
                    cur.execute(
                         "INSERT INTO server_log ("
                         "server_type, clients_total,"
                         "error_type, message, timestamp"
                         ") VALUES (?, ?, ?, ?, ?)",
                         (
                          row["server_type"],
                          row["clients_total"],
                          row["error_type"],
                          row["message"],
                          row["timestamp"]
                         ))
                elif row['log_type'] == 'client':
                    cur.execute(
                         "INSERT INTO test ("
                         "server_type, client_id, conn_attempt,"
                         "clients_total, send_id, t_send_attempt,"
                         "t_send_success, t_server_response, t_response, error"
                         ")"
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (
                          row["server_type"],
                          row["client_id"],
                          row["conn_attempt"],
                          row["clients_total"],
                          row["send_id"],
                          row["t_send_attempt"],
                          row["t_send_success"],
                          row["t_server_response"],
                          row["t_response"],
                          row.get("error")
                         ))
                # print('sended')
                # que.task_done()
        except Exception as ex:
            print(ex)
                # break
        finally:
            conn.commit()
            print(que.name, f'sended, {que.qsize()} left')


def extract_table_name(query: str) -> str | None:
    match = re.search(r'\bFROM\s+([^\s;]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def get_from_base(
 query: str='', mode: str='full table',\
 db_name: str=DB_NAME) -> list[str] | tuple[list[str], list[tuple[Any, ...]]]:
    if not query:
        query = get_query('basic_stats')
    with sqlite3.connect(DB_NAME) as conn:

        if mode == 'templates':
            table_name = extract_table_name(query)
            if not table_name:
                print('Table name not exists')
            return []
            cur = conn.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cur.fetchall()]
        cur = conn.cursor()
        cur.execute(query)

        columns = [desc[0] for desc in cur.description]
        result = cur.fetchall()
        return columns, result
