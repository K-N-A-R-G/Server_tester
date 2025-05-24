# types_common.py

from typing import Any, Mapping, TypedDict, Optional, Literal
import queue


class LogData(TypedDict):
    log_type: Literal['client']
    server_type: str
    client_id: int | None
    clients_total: int
    conn_attempt: Optional[int]
    t_send_attempt: Optional[float]
    send_id: Optional[int]
    t_send_success: Optional[float]
    t_server_response: Optional[float]
    t_response: Optional[float]
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
