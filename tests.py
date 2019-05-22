import os

from cysqlite import *


conn = Connection(':memory:')
conn.connect()

r = conn.execute('create table kv (id integer not null primary key, key text, '
                 'value text)')
print(r)

r = conn.execute('insert into kv (key, value) values (?, ?), (?, ?), (?, ?)',
                 ('k1', 'v1x', 'k2', 'v2', 'k3', 'v3zzz'))
print(r)
print(conn.last_insert_rowid())

print('-' * 70)

curs = conn.execute('select * from kv where key > ? order by key desc', ('k1',))
for row in curs:
    print(row)

with conn.atomic() as txn:
    conn.execute('insert into kv (key, value) values (?, ?)', ('k4', 'v4a'))
    txn.rollback()

with conn.atomic() as txn:
    with conn.atomic() as sp:
        conn.execute('insert into kv (key, value) values (?, ?)', ('k5', 'v5'))
    with conn.atomic() as sp:
        conn.execute('insert into kv (key, value) values (?, ?)', ('k5', 'v5'))
        sp.rollback()
    conn.execute('insert into kv (key, value) values (?, ?)', ('k7', 'v7'))

print('-' * 70)

curs = conn.execute('select * from kv where key > ? order by key desc', ('k2',))
for row in curs:
    print(row)

conn.execute_simple('drop table kv')
conn.close()

print('-' * 70)

conn.connect()
conn.execute('create table foo (id integer not null primary key, key text)')
conn.execute('insert into foo (key) values (?), (?), (?), (?)',
             ('k1', 'k2', 'k3', 'k4'))
for row in conn.execute('select * from foo'):
    print(row[0], '->', row[1])

try:
    conn.execute('select * from zoo;')
except Exception as exc:
    print(exc)

conn.execute('delete from foo where id < ?', (3,))
print(conn.changes())

conn.close()

# Test statement cache.
conn = Connection(':memory:', cached_statements=2)
conn.connect()

conn.execute('create table foo (key text, value text)')
with conn.atomic():
    for k, v in zip('abcdefg', 'hijklmno'):
        conn.execute('INSERT INTO foo (key, value) VALUES (?, ?)', (k, v))

    list(conn.execute('select * from foo'))
    list(conn.execute('select * from foo'))

conn.close()
