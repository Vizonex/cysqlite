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

curs = conn.execute('select * from kv order by key desc')
for row in curs:
    print(row)

conn.execute_simple('drop table kv')
conn.close()

conn.connect()
conn.execute('create table foo (id integer not null primary key, key text)')
conn.execute('insert into foo (key) values (?), (?), (?), (?)',
             ('k1', 'k2', 'k3', 'k4'))
for row in conn.execute('select * from foo'):
    print(row[0], '->', row[1])

conn.execute('delete from foo where id < ?', (3,))
print(conn.changes())
conn.close()
