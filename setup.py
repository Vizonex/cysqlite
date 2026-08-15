import os
import sys

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


def _have_load_extension():
    override = os.environ.get('CYSQLITE_LOAD_EXTENSION')
    if override is not None:
        return override.strip().lower() not in ('0', 'false', 'no', '')

    import tempfile
    import shutil
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler

    tmp = tempfile.mkdtemp(prefix='cysqlite-probe-')
    try:
        probe = os.path.join(tmp, 'probe.c')
        with open(probe, 'w') as fh:
            fh.write('#include "sqlite3.h"\n'
                     'int main(void){ return sqlite3_enable_load_extension == 0; }\n')
        cc = new_compiler()
        customize_compiler(cc)
        saved = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
        try:
            cc.compile([probe], output_dir=tmp)
            return True
        except Exception:
            return False
        finally:
            os.dup2(saved, 2)
            os.close(saved)
            os.close(devnull)
    except Exception:
        # Fallback, assume we have it if we're not crapple.
        return sys.platform != 'darwin'
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

link_args = []

# Determine how we are building cysqlite. A sqlite3.c/sqlite3.h pair in the
# project root is compiled in, otherwise we link against the system sqlite3.
if os.path.exists('sqlite3mc_amalgamation.c') or \
   os.path.exists('sqlite3mc_amalgamation.h'):
    raise SystemExit('cysqlite: rename sqlite3mc_amalgamation.c and '
                     'sqlite3mc_amalgamation.h to sqlite3.c and sqlite3.h, '
                     'then rebuild.')

have_src = os.path.exists('sqlite3.c')
have_hdr = os.path.exists('sqlite3.h')
if have_src != have_hdr:
    raise SystemExit('cysqlite: embedded builds require both sqlite3.c and '
                     'sqlite3.h, only %s is present.'
                     % ('sqlite3.c' if have_src else 'sqlite3.h'))


def _amalgamation_flavor():
    """
    Classify sqlite3.c by content: sqlite3mc, sqlcipher or plain sqlite.
    sqlite3mc also contains sqlcipher compatibility strings, so test it first.
    """
    with open('sqlite3.c', 'rb') as fh:
        data = fh.read()
    if b'sqlite3mc' in data:
        return 'sqlite3mc'
    elif b'sqlcipher' in data:
        return 'sqlcipher'
    return 'sqlite'


use_sqlcipher = False

if have_src:
    flavor = _amalgamation_flavor()
    override = os.environ.get('SQLCIPHER')
    if override is None:
        use_sqlcipher = flavor == 'sqlcipher'
    elif override.strip().lower() in ('0', 'false', 'no', ''):
        use_sqlcipher = False
    elif flavor == 'sqlcipher':
        use_sqlcipher = True
    else:
        raise SystemExit('cysqlite: SQLCIPHER was requested but sqlite3.c '
                         'is %s.' % flavor)

    if flavor == 'sqlcipher' and not use_sqlcipher:
        note = ' (sqlcipher, codec disabled)'
    elif flavor != 'sqlite':
        note = ' (%s)' % flavor
    else:
        note = ''
    print('cysqlite: building with bundled sqlite3.c%s' % note)

    sources.append('sqlite3.c')
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
        ('CYSQLITE_HAVE_LOAD_EXTENSION', 1),
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

    if use_sqlcipher:
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
    else:
        define_macros.extend([
            ('SQLITE_TEMP_STORE', 3),
        ])

else:
    print('cysqlite: building against system sqlite3')
    include_dirs = []
    libraries = ['sqlite3']
    define_macros = [
        ('CYSQLITE_HAVE_LOAD_EXTENSION', 1 if _have_load_extension() else 0),
    ]

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
