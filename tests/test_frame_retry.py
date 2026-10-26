"""A report query survives a dropped link, whichever error psycopg2 raises for it."""
from types import SimpleNamespace

import psycopg2
import pytest

from report import frame


class FakeConn:
    def __init__(self, error=None):
        self.error, self.closed = error, False

    def cursor(self):
        conn = self

        class Cur:
            description = [SimpleNamespace(name="x")]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, params=None):
                if conn.error:
                    raise conn.error

            def fetchall(self):
                return [(1,), (2,)]
        return Cur()

    def close(self):
        self.closed = True


@pytest.mark.parametrize("error", [psycopg2.OperationalError("timed out"), psycopg2.InterfaceError("connection already closed")])
def test_query_retries_a_dropped_link(monkeypatch, error):
    conns = iter([FakeConn(error), FakeConn()])
    monkeypatch.setattr(frame.psycopg2, "connect", lambda *a, **k: next(conns))
    monkeypatch.setattr(frame.time, "sleep", lambda s: None)
    monkeypatch.setenv("DATABASE_URL_RO", "postgres://unused")
    assert frame.query("SELECT 1").x.tolist() == [1, 2]
