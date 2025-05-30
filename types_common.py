# types_common.py

from typing import TypedDict, Literal
import queue


class LogData(TypedDict):
    log_type: Literal['client']
    server_type: str
    client_id: int | None
    clients_total: int
    conn_attempt: int | None
    t_send_attempt: float | None
    send_id: int | None
    t_send_success: float | None
    t_server_response: float | None
    t_response: float | None
    error: str


class ServerLogData(TypedDict):
    log_type: Literal['server']
    server_type: str
    clients_total: int
    error_type: str
    message: str
    timestamp: float


LogDict = LogData | ServerLogData


class NamedQueue(queue.Queue[LogDict]):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
