"""Django request-style connection lifetime for synchronous MCP worker threads."""
from functools import wraps

from django.db import close_old_connections, connections


def database_tool(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        # MCP tools do not pass through Django's request_started/finished signals.
        # Respect a caller-owned transaction (including Django TestCase).
        if not any(connection.in_atomic_block for connection in connections.all()):
            close_old_connections()
        try:
            return function(*args, **kwargs)
        finally:
            for connection in connections.all():
                if not connection.in_atomic_block:
                    connection.close()
    return wrapped
