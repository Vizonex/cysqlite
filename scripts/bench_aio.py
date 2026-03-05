import asyncio
import contextlib
import time

import cysqlite
from cysqlite.aio import connect as aconnect

@contextlib.contextmanager
def measure(name):
    s = time.perf_counter()
    yield
    e = time.perf_counter()
    print('%0.2f - %s' % (e - s, name))

def test_execute():
    db = cysqlite.connect(':memory:')
    db.execute('create table k (data)')
    db.executemany('insert into k (data) values (?)',
                   [('k%06d' % i,) for i in range(10000)])

    with measure('iterate'):
        for i in range(1000):
            db.execute('select * from k').fetchall()

    db.execute('drop table k')

async def test_aexecute():
    adb = aconnect(':memory:')
    await adb.execute('create table k (data)')
    await adb.executemany('insert into k (data) values (?)',
                          [('k%06d' % i,) for i in range(10000)])

    with measure('iterate (async)'):
        for i in range(1000):
            curs = await adb.execute('select * from k')
            await curs.fetchall()

    await adb.execute('drop table k')

test_execute()
asyncio.run(test_aexecute())
