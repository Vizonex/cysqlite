import asyncio
import queue
import threading
from collections import deque
from functools import partial
from cysqlite._cysqlite import connect as _connect
from cysqlite._cysqlite import Connection
from cysqlite._cysqlite import Row


SHUTDOWN = object()


class AsyncConnection(object):
    def __init__(self, conn, loop):
        self.conn = conn
        self.loop = loop
        self.queue = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while True:
            item = self.queue.get()
            if item is SHUTDOWN:
                break
            fn, fut = item
            try:
                result = fn()
            except BaseException as exc:
                self.loop.call_soon_threadsafe(fut.set_exception, exc)
            else:
                self.loop.call_soon_threadsafe(fut.set_result, result)

    def _submit(self, fn):
        fut = self.loop.create_future()
        self.queue.put((fn, fut))
        return fut

    async def execute(self, sql, params=None):
        cursor = await self._submit(partial(self.conn.execute, sql, params))
        return AsyncCursor(self, cursor)

    async def executemany(self, sql, seq_of_params):
        cursor = await self._submit(partial(self.conn.executemany, sql,
                                            seq_of_params))
        return AsyncCursor(self, cursor)

    async def executescript(self, sql):
        cursor = await self._submit(partial(self.conn.executescript, sql))
        return AsyncCursor(self, cursor)

    async def execute_one(self, sql, params=None):
        return await self._submit(partial(self.conn.execute_one, sql, params))

    async def execute_scalar(self, sql, params=None):
        return await self._submit(partial(self.conn.execute_scalar, sql,
                                          params))

    async def commit(self):
        await self._submit(self.conn.commit)

    async def rollback(self):
        await self._submit(self.conn.rollback)

    async def close(self):
        await self._submit(self.conn.close)
        self.queue.put(SHUTDOWN)
        # Join from the event loop?

    async def last_insert_rowid(self):
        return await self._submit(self.conn.last_insert_rowid)

    def join(self, timeout=None):
        self._thread.join(timeout)

    async def backup(self, dest, **kwargs):
        await self._submit(partial(self.conn.backup, dest.conn, **kwargs))

    async def backup_to_file(self, filename, **kwargs):
        await self._submit(partial(self.conn.backup_to_file, filename,
                                   **kwargs))

    async def checkpoint(self, **kwargs):
        return await self._submit(partial(self.conn.checkpoint, **kwargs))

    def transaction(self, lock=None):
        return AsyncTransaction(self, lock)

    def savepoint(self, sid=None):
        return AsyncSavepoint(self, sid)

    def atomic(self, lock=None):
        return AsyncAtomic(self, lock)

    @property
    def in_transaction(self):
        return self.conn.in_transaction

    def pragma(self, *args, **kwargs):
        return self._submit(partial(self.conn.pragma, *args, **kwargs))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AsyncCursor:
    def __init__(self, conn, cursor):
        self.conn = conn
        self._cursor = cursor
        self._buffer = []

    async def fetchone(self):
        return await self.conn._submit(self._cursor.fetchone)

    async def fetchall(self):
        return await self.conn._submit(self._cursor.fetchall)

    async def scalar(self):
        return await self.conn._submit(self._cursor.scalar)

    @property
    def description(self):
        return self._cursor.description

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __aiter__(self):
        return self

    async def fetchmany(self, size=100, constructor=list):
        def _fetch():
            rows = constructor()
            for _ in range(size):
                try:
                    rows.append(self._cursor.__next__())
                except StopIteration:
                    break
            return rows
        return await self.conn._submit(_fetch)

    def __aiter__(self):
        return self

    async def __anext__(self):
        # Use internal buffer to amortize dispatch cost.
        if not self._buffer:
            self._buffer = await self.fetchmany(100, deque)
            if not self._buffer:
                raise StopAsyncIteration
        return self._buffer.popleft()


class _AsyncTransactionWrapper(object):
    def __init__(self, conn, *args):
        self.conn = conn
        self._sync_conn = conn.conn
        self._args = args

    def get_wrapper(self):
        raise NotImplementedError

    async def __aenter__(self):
        self._txn = self.get_wrapper()
        await self.conn._submit(self._txn.__enter__)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn._submit(partial(self._txn.__exit__, exc_type, exc_val,
                                        exc_tb))

    async def commit(self, *args):
        await self.conn._submit(partial(self._txn.commit, *args))

    async def rollback(self, *args):
        await self.conn._submit(partial(self._txn.rollback, *args))


class AsyncTransaction(_AsyncTransactionWrapper):
    def get_wrapper(self):
        return self._sync_conn.transaction(*self._args)

class AsyncSavepoint(_AsyncTransactionWrapper):
    def get_wrapper(self):
        return self._sync_conn.savepoint(*self._args)

class AsyncAtomic(_AsyncTransactionWrapper):
    def get_wrapper(self):
        return self._sync_conn.atomic(*self._args)

    async def commit(self, *args):
        await self.conn._submit(partial(self._txn.txn.commit, *args))

    async def rollback(self, *args):
        await self.conn._submit(partial(self._txn.txn.rollback, *args))


def connect(database, **kwargs):
    loop = asyncio.get_running_loop()
    conn = _connect(database, **kwargs)
    return AsyncConnection(conn, loop=loop)
