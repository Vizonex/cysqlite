.. _installation:

Installation
============

cysqlite can be installed four ways. Pick the one that fits:

* Binary wheel, SQLite embedded, no build needed: ``pip install cysqlite``.
* Source build against the system SQLite:
  ``pip install --no-binary :all: cysqlite``.
* Self-contained build embedding a SQLite of your choosing, see
  :ref:`custom-builds`.
* Encrypted builds, see :ref:`sqlcipher-build` or :ref:`sqlite3mc-build`.

Wheels
------

.. code-block:: shell

    pip install cysqlite

Wheels embed the SQLite release current at the time the cysqlite release was
made, compiled with full-text search, JSON, r*tree, stat4, math functions,
soundex, update/delete limit, and extension support. Check any build with
:func:`compile_option`:

.. code-block:: python

    >>> import cysqlite
    >>> cysqlite.sqlite_version
    '3.53.3'
    >>> cysqlite.compile_option('ENABLE_FTS5')
    True

Building from source
--------------------

Source builds need a C compiler and the Python development headers. Building
against the system SQLite additionally needs the SQLite development headers
(``libsqlite3-dev`` on Debian, ``sqlite-devel`` on Fedora):

.. code-block:: shell

    # Build against the system sqlite.
    pip install --no-binary :all: cysqlite

To install the very latest commit:

.. code-block:: shell

    # (note: links against system sqlite)
    pip install -e git+https://github.com/coleifer/cysqlite.git#egg=cysqlite

.. _custom-builds:

Custom Builds
-------------

When a ``sqlite3.c`` / ``sqlite3.h`` pair is present in the root of the
cysqlite checkout, it is compiled into the extension and the result is fully
self-contained. The ``fetch_sqlite`` script downloads an amalgamation into
place, either the current release or any `release <https://www.sqlite.org/chronology.html>`_
you name:

.. code-block:: shell

    git clone https://github.com/coleifer/cysqlite
    cd cysqlite/

    ./scripts/fetch_sqlite         # Current release, or:
    ./scripts/fetch_sqlite 3.51.2  # A specific version.

    pip install .

The build prints the mode it resolved, e.g. ``cysqlite: building with
bundled sqlite3.c``. Verify the result:

.. code-block:: python

    >>> import cysqlite
    >>> cysqlite.sqlite_version
    '3.51.2'

When switching between build flavors, remove the ``build/`` directory first
so no stale objects are reused.

Self-contained sdist
--------------------

A source distribution built from a checkout containing an amalgamation
includes it, and installing that sdist produces a self-contained build. This
is useful for distributing a pinned cysqlite+SQLite internally:

.. code-block:: shell

    ./scripts/fetch_sqlite 3.51.2
    python -m build --sdist  # dist/cysqlite-*.tar.gz embeds sqlite 3.51.2.

.. _sqlcipher-build:

SQLCipher
---------

`SQLCipher <https://github.com/sqlcipher/sqlcipher>`_ provides encryption.
It does not publish a source amalgamation, so cysqlite includes a script
that builds one. The script requires git, make, a C compiler and the OpenSSL
development headers (``libssl-dev`` on Debian):

.. code-block:: shell

    git clone https://github.com/coleifer/cysqlite
    cd cysqlite/

    ./scripts/fetch_sqlcipher         # Latest, or:
    ./scripts/fetch_sqlcipher v4.7.0  # A specific tag.

    pip install .

SQLCipher sources are detected automatically and the build announces
``cysqlite: building with bundled sqlite3.c (sqlcipher)``. Set
``SQLCIPHER=0`` to compile the same sources with the codec disabled.
Verify:

.. code-block:: python

    >>> db = cysqlite.connect('app.db')
    >>> db.execute_one('PRAGMA cipher_version')
    ('4.17.0 community',)

.. _sqlite3mc-build:

SQLite Multiple Ciphers
-----------------------

`SQLite3 Multiple Ciphers <https://utelle.github.io/SQLite3MultipleCiphers/>`_
also provides encryption, with no external crypto dependency. The
``fetch_sqlite3mc`` script downloads a release amalgamation and renames it
into place:

.. code-block:: shell

    git clone https://github.com/coleifer/cysqlite
    cd cysqlite/

    ./scripts/fetch_sqlite3mc         # Latest release, or:
    ./scripts/fetch_sqlite3mc v2.5.0  # A specific tag.

    pip install .

Or do the same by hand with a zip from the
`releases page <https://github.com/utelle/SQLite3MultipleCiphers/releases>`_:

.. code-block:: shell

    unzip sqlite3mc-*-amalgamation.zip 'sqlite3mc_amalgamation.*'
    mv sqlite3mc_amalgamation.c cysqlite/sqlite3.c
    mv sqlite3mc_amalgamation.h cysqlite/sqlite3.h

The build announces ``cysqlite: building with bundled sqlite3.c
(sqlite3mc)``. Verify:

.. code-block:: python

    >>> db = cysqlite.connect('app.db')
    >>> db.execute("PRAGMA key='passphrase'")
    >>> db.execute_one('PRAGMA cipher')
    ('chacha20',)
