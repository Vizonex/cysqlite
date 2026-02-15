import os
import sys
import warnings

from setuptools import setup
from setuptools.extension import Extension
try:
    from Cython.Build import cythonize
    cython_installed = True
except ImportError:
    cython_installed = False

if cython_installed:
    sources = ['src/cysqlite/_cysqlite.pyx']
else:
    sources = ['src/cysqlite/_cysqlite.c']
    cythonize = lambda obj: obj

compile_args = ['-O3', '-Wall'] if sys.platform != 'win32' else ['/O2']
if os.environ.get('DEBUG') and sys.platform != 'win32':
    compile_args = ['-O0', '-Wall']

link_args = []

# Determine how we are building cysqlite.
sqlite_source = None
is_sqlite_mc = False

if os.path.exists('sqlite3.c') and os.path.exists('sqlite3.h'):
    sqlite_source = 'sqlite3.c'
elif os.path.exists('sqlite3mc_amalgamation.c') and \
     os.path.exists('sqlite3mc_amalgamation.h'):
    sqlite_source = 'sqlite3mc_amalgamation.c'
    is_sqlite_mc = True

if sqlite_source:
    sources.append(sqlite_source)
    include_dirs = ['.']
    libraries = []
    define_macros = [
        ('SQLITE_ALLOW_COVERING_INDEX_SCAN', 1),
        ('SQLITE_ENABLE_FTS3', 1),
        ('SQLITE_ENABLE_FTS3_PARENTHESIS', 1),
        ('SQLITE_ENABLE_FTS4', 1),
        ('SQLITE_ENABLE_FTS5', 1),
        ('SQLITE_ENABLE_JSON1', 1),
        ('SQLITE_ENABLE_LOAD_EXTENSION', 1),
        ('SQLITE_ENABLE_MATH_FUNCTIONS', 1),
        ('SQLITE_ENABLE_RTREE', 1),
        ('SQLITE_ENABLE_STAT4', 1),
        ('SQLITE_ENABLE_UPDATE_DELETE_LIMIT', 1),
        ('SQLITE_SOUNDEX', 1),
        ('SQLITE_USE_URI', 1),
        ('SQLITE_MAX_VARIABLE_NUMBER', 250000),
        ('SQLITE_MAX_MMAP_SIZE', 2**40),
        ('inline', '__inline'),
    ]

    if os.environ.get('SQLCIPHER'):
        define_macros.extend([
            ('SQLITE_HAS_CODEC', '1'),
            ('SQLITE_SECURE_DELETE', '1'),
            ('SQLITE_TEMP_STORE', '2'),
            ('SQLITE_THREADSAFE', '1'),
            ('SQLITE_EXTRA_INIT', 'sqlcipher_extra_init'),
            ('SQLITE_EXTRA_SHUTDOWN', 'sqlcipher_extra_shutdown'),
            ('HAVE_STDINT_H', '1'),
        ])
        if sys.platform == 'win32':
            link_args.extend([
                'WS2_32.LIB', 'GDI32.LIB', 'ADVAPI32.LIB', 'CRYPT32.LIB',
                'USER32.LIB', 'libcrypto.lib'])
        else:
            link_args.extend(['-lcrypto'])
    elif os.environ.get('SQLITEMC') or is_sqlite_mc:
        define_macros.extend([
            ('SQLITE_SECURE_DELETE', '1'),
            ('SQLITE_TEMP_STORE', '2'),
            ('SQLITE_THREADSAFE', '1'),
        ])
    else:
        define_macros.extend([
            ('SQLITE_TEMP_STORE', 3),
        ])

else:
    include_dirs = []
    libraries = ['sqlite3']
    define_macros = []

cysqlite_extension = Extension(
    'cysqlite._cysqlite',
    sources=sources,
    include_dirs=include_dirs,
    libraries=libraries,
    define_macros=define_macros,
    extra_compile_args=compile_args,
    extra_link_args=link_args)

constants_extension = Extension(
    'cysqlite._constants',
    include_dirs=include_dirs,
    libraries=libraries,
    sources=['src/cysqlite/_constants.c'])

setup(ext_modules=cythonize([cysqlite_extension]) + [constants_extension])
