from cysqlite import *

conn = Connection('/tmp/xx.db')
conn.connect()

conn.execute('drop table if exists "kv"')
conn.execute('create table if not exists "kv" ('
             '"id" integer not null primary key, '
             '"key" text not null, '
             '"value" text not null)')

st = Statement(conn, 'insert into kv (key, value) values (?,?),(?,?),(?,?)',
               ('k1', 'v1x', 'k2', 'v2yy', 'k3', 'v3'))
print(st.execute())

def cb(row):
    print(row)

conn.execute('select * from kv', cb)

st = Statement(conn, "select * from kv")
print(st.execute())

conn.close()
