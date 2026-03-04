# db_utils.py

import re
import sqlite3

from query_loader import get_query
from typing import Any
from types_common import NamedQueue


DB_NAME = "statistics.sqlite"


def init_db(DB_NAME: str=DB_NAME, new: bool=False) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        #  Write-Ahead Logging (WAL) mode in SQLite:
        #  Increased concurrency;
        #  Faster write performance;
        #  Fewer fsync() calls;
        #  Automatic checkpointing;
        #  Should be set immediately after connecting to the database
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


def _write_log(cursor, row):
    if row['log_type'] == 'server':
        cursor.execute(
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
        cursor.execute(
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


def send_to_base(
 data_source: NamedQueue | dict, db_name: str=DB_NAME) -> None:
    with sqlite3.connect(db_name) as conn:
        conn.execute("PRAGMA journal_mode=WAl;")
        cur = conn.cursor()

        if isinstance(data_source, dict):
            _write_log(cur, data_source)
        else:
            print(data_source.name, f'connected, ({data_source.qsize()} elements)')
            try:
                while (row := data_source.get(timeout=1)) != 'End':  # type: ignore
                    _write_log(cur, row)
            except Exception as ex:
                print('sending:', ex)
                # break
            finally:
                conn.commit()
                print(data_source.name, f'sended, {data_source.qsize()} left')


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
