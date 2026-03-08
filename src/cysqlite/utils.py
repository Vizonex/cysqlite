import logging
import queue
import threading

from cysqlite import connect
from cysqlite import SQLITE_OPEN_CREATE
from cysqlite import SQLITE_OPEN_READONLY
from cysqlite import SQLITE_OPEN_READWRITE
from cysqlite import SQLITE_OPEN_WAL
from cysqlite import SQLITE_TRACE_PROFILE
from cysqlite.exceptions import InterfaceError


def slow_query_log(conn, threshold_ms=50, logger=None, level=logging.WARNING,
                   expand_sql=True):
    log = logging.getLogger(logger or __name__)
    def trace(event, sid, sql, ns):
        if not sql:
            return
        ms = ns / 1000000
        if ms >= threshold_ms:
            log.log(level, 'Slow query %0.1fms: %s', ms, sql)

    conn.trace(trace, SQLITE_TRACE_PROFILE, expand_sql=expand_sql)
    return True


class Pool(object):
    default_pragmas = {
        'journal_mode': 'wal',
        'cache_size': 64 * -1000,
        'mmap_size': 256 * 1024 * 1024,
        'foreign_keys': 1,
    }

    def __init__(self, database, readers=4, writer=True, **connect_kwargs):
        self.database = database
        self._connect_kwargs = connect_kwargs
        self._readers = queue.SimpleQueue()
        self._writer_lock = threading.Lock()
        self._writer = None
        self._closed = False

        # Apply overrides.
        connect_kwargs.setdefault('timeout', 2.0)
        pragmas = connect_kwargs.setdefault('pragmas', {})
        for key, value in self.default_pragmas.items():
            pragmas.setdefault(key, value)

        if writer:
            self._writer = self._connect(read_only=False)

        for _ in range(readers):
            self._readers.put(self._connect(read_only=True))

    def _connect(self, read_only=False):
        if read_only:
            flags = SQLITE_OPEN_READONLY | SQLITE_OPEN_WAL
        else:
            flags = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE

        conn = connect(self.database, flags=flags, **self._connect_kwargs)
        return conn

    def reader(self):
        if self._closed:
            raise InterfaceError('Pool is closed')
        return _Reader(self)

    def writer(self):
        if self._closed:
            raise InterfaceError('Pool is closed')
        return _Writer(self)

    def close(self):
        self._closed = True
        if self._writer:
            self._writer.close()
            self._writer = None
        while not self._readers.empty():
            try:
                conn = self._readers.get_nowait()
                conn.close()
            except queue.Empty:
                break


class _ConnectionContext(object):
    def __init__(self, pool):
        self.pool = pool
        self.conn = None

class _Reader(_ConnectionContext):
    def __enter__(self):
        self.conn = self.pool._readers.get()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            self.pool._readers.put(self.conn)
            self.conn = None

class _Writer(_ConnectionContext):
    def __enter__(self):
        self.pool._writer_lock.acquire()
        self.conn = self.pool._writer
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.conn.in_transaction:
                self.conn.rollback()
        finally:
            self.conn = None
            self.pool._writer_lock.release()
