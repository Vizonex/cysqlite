from cysqlite import Connection

conn = Connection('/tmp/xx.db')
conn.connect()
conn.close()
