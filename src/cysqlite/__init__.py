from cysqlite._cysqlite import *
from cysqlite.exceptions import *


version = __version__ = '0.1.4'
version_info = tuple(int(i) for i in version.split('.'))

# DB-API 2.0 module attributes.
apilevel = '2.0'
paramstyle = 'qmark'
