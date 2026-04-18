.. _sqlite-notes:

SQLite Notes
============

SQLite's type system is different from other databases. SQLite stores data in
five simple types:

+-------------------------------+-------------+
| Python type                   | SQLite type |
+===============================+=============+
| ``None``                      | ``NULL``    |
+-------------------------------+-------------+
| ``int``, ``bool``             | ``INTEGER`` |
+-------------------------------+-------------+
| ``float``, ``Decimal``        | ``REAL``    |
+-------------------------------+-------------+
| ``str``                       | ``TEXT``    |
+-------------------------------+-------------+
| ``bytes`` / buffers           | ``BLOB``    |
+-------------------------------+-------------+

Notably SQLite does not natively support:

* **datetime / date** - store these as ISO-formatted text or as unix timestamps.
* **fixed-precision decimals** - no native type. cysqlite stores ``Decimal`` as
  ``REAL`` by default, which can lose precision for values that aren't exactly
  representable as floats. Register a custom :ref:`adapter <sqlite-notes-adapters>`
  to store as ``TEXT`` if exact precision is required.
* **boolean** - emulated as integer ``1`` and ``0``.
* **json** - SQLite has JSON support, but it is stored as ``TEXT`` or ``BLOB``
  (for JSONB).

SQLite will store any value in a column regardless of its declared type, using
`type affinity <https://www.sqlite.org/datatype3.html#type_affinity>`_ to
influence how the data is stored. Strict typing is opt-in with `strict tables <https://www.sqlite.org/stricttables.html>`_
(requires SQLite 3.37.0+).

For convenience, cysqlite applies the following rules for adapting Python types
to match SQLite's available data-types:

+-------------------------------+-------------------------------------------+
| Python type                   | SQLite type                               |
+===============================+===========================================+
| ``datetime``                  | ``TEXT`` (isoformat with ' ' delimiter).  |
+-------------------------------+-------------------------------------------+
| ``date``                      | ``TEXT`` (isoformat)                      |
+-------------------------------+-------------------------------------------+
| ``Fraction``, ``Decimal``,    | ``REAL``                                  |
| ``__float__()``               |                                           |
+-------------------------------+-------------------------------------------+
| **Anything else**             | ``TEXT`` (coerced to ``str()``) or custom |
|                               | via :meth:`Connection.register_adapter`.  |
+-------------------------------+-------------------------------------------+

Examples:

.. code-block:: python

   values = [
       None,
       1,
       2.3,
       'a text \u2012 string',
       b'\x00\xff\x00\xff',
       bytearray(b'this is a buffer'),
       datetime(2026, 1, 2, 3, 4, 5).astimezone(timezone.utc),
       datetime(2026, 2, 3, 4, 5, 6),
       date(2026, 3, 4),
       uuid.uuid4(),  # str()
   ]

   for value in values:
       row = db.execute_one('select typeof(?), ?', (value, value))
       print(row)

   # ('null',    None)
   # ('integer', 1)
   # ('real',    2.3)
   # ('text',    'a text ‒ string')
   # ('blob',    b'\x00\xff\x00\xff')
   # ('blob',    b'this is a buffer')
   # ('text',    '2026-01-02 03:04:05+00:00')
   # ('text',    '2026-02-03 04:05:06')
   # ('text',    '2026-03-04')
   # ('text',    '0c4ca10a-56ab-470a-9357-d28366d97ceb')

.. _sqlite-notes-adapters:

Adapters
---------

You can add custom adapters to control exactly how Python types are sent to
SQLite using :meth:`Connection.register_adapter` and the :meth:`~Connection.adapter`
decorator. For example, it may be desirable to store ``Decimal`` values as
``TEXT`` in order to avoid float-point precision issues, or to store ``date``
as an 8-digit integer:

.. code-block:: python

   db.register_adapter(Decimal, str)

   @db.adapter(datetime.date)
   def adapt_date(value):
       return int(value.strftime('%Y%m%d'))

   values = [
       date(2026, 3, 4),
       Decimal('1.3'),
   ]

   for value in values:
       row = db.execute_one('select typeof(?), ?', (value, value))
       print(row)

   # ('integer', 20260304)
   # ('text',    '1.3')

.. _sqlite-converters:

Converters
-----------

By default, no special attempts at type inference are applied to data coming
**from** SQLite. As you can see in the above examples, all our Python values
were coerced to reasonable SQLite-friendly representations. But that richness
is lost when reading data from SQLite into Python without specific helpers that
read each column's declared type.

To convert data going from SQLite into Python, you will need to register one or
more converters using :meth:`Connection.register_converter` or using the
:meth:`Connection.converter` decorator. Converters rely on the SQLite
`sqlite3_column_decltype <https://www.sqlite.org/c3ref/column_decltype.html>`_
API, which retrieves the declared type of the given column. cysqlite then
applies your converter for any type that was registered.

For example, to convert columns declared ``DATETIME`` back to Python datetimes:

.. code-block:: python

   db = cysqlite.connect(':memory:')

   db.register_converter('datetime', datetime.datetime.fromisoformat)

   # Or use a decorator:
   @db.converter('datetime')
   def convert_datetime(value):
       # Converts our ISO-formatted date string into a python datetime.
       return datetime.datetime.fromisoformat(value)

If the value is ``NULL`` then the convert function is **not** applied, so you
do not need to test for ``value is None``.

Below are some examples:

.. code-block:: python

   db = cysqlite.connect(':memory:')

   @db.converter('datetime')
   def convert_datetime(value):
       # Converts our ISO-formatted date string into a python datetime.
       return datetime.datetime.fromisoformat(value)

   # Automatically parse and load data declared as JSON.
   db.register_converter('json', json.loads)

   # Handle decimal data.
   @db.converter('numeric')
   def convert_numeric(value):
       return Decimal(value).quantize(Decimal('1.00'))

   db.execute('create table vals (ts datetime, js json, dec numeric(10, 2))')

   # Create a TZ-aware datetime and a JSON object.
   ts = datetime.datetime(2026, 1, 2, 3, 4, 5).astimezone(datetime.timezone.utc)
   js = {'key': {'nested': 'value'}, 'arr': ['i0', 1, 2., None]}
   dec = Decimal('1.3')

   # When we INSERT the JSON, note that we need to dump it to string.
   db.execute('insert into vals (ts, js, dec) values (?, ?, ?)',
              (ts, json.dumps(js), dec))

   # When reading back the data, it is converted automatically based on
   # the declared column types.
   row = db.execute_one('select * from vals')
   assert row == (ts, js, dec)

The converter accepts a ``data_type`` and uses the following rules for matching
a specified data-type to what SQLite tells us:

* Matching is case-insensitive, e.g. ``JSON`` or ``json`` is fine.
* Split on the first whitespace or ``"("`` character, e.g. if SQLite
  tells us the data-type is ``NUMERIC(10, 2)``, cysqlite will attempt to
  find a converter named ``numeric``.

Differences from stdlib
-----------------------

The stdlib ``sqlite3`` module uses different conventions for registering
adapters and converters:

* Adapters and converters in ``sqlite3`` are registered *globally*. In
  ``cysqlite``, they are scoped to the :class:`Connection`.
* ``sqlite3`` converters — functions that transform values coming *from*
  SQLite back into richer Python types — are disabled by default, and are
  enabled via the ``detect_types`` parameter on ``connect()``. Two modes
  are available: matching against the column's declared type
  (``PARSE_DECLTYPES``) and matching against a type hint embedded in a
  column alias (``PARSE_COLNAMES``). cysqlite always matches against
  declared types, and has no column-alias mechanism.
* ``sqlite3`` has a separate adaptation mechanism that checks for a
  ``__conform__()`` method on the object being bound; the method's return
  value is used in place of the original. cysqlite has no equivalent —
  bind either a supported type directly, or register an adapter.
* ``sqlite3`` historically shipped default adapters for ``datetime`` and
  ``date``, and also handled ``datetime`` via two magic type names, but
  these are deprecated as of Python 3.12.

cysqlite is more permissive about what types it will accept at bind time. Any
object with a ``__float__`` method (e.g. ``Decimal``, ``Fraction``) is bound as
``REAL``, and anything else falls back to ``str(x)`` rather than raising
``TypeError``. Additionally, cysqlite provides ISO-8601 formatting for
``datetime`` and ``date`` out of the box with no surprise deprecations.
Sqlite's built-in `date functions <https://sqlite.org/lang_datefunc.html>`_
work well on ISO-8601 format, so this allows date/times stored by ``cysqlite``
to be usable with the builtin date functions.
