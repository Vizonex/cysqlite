from cysqlite import Connection

conn = Connection('/tmp/xx.db')
conn.connect()

def cb(row):
    print(row)

conn.execute('select * from kv', cb)

conn.close()
