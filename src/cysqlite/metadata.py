from collections import namedtuple


Index = namedtuple(
    'Index', (
        'name',
        'sql',
        'columns',
        'unique',
        'table'))

Column = namedtuple(
    'Column', (
        'name',
        'data_type',
        'null',
        'primary_key',
        'table',
        'default'))

ForeignKey = namedtuple(
    'ForeignKey', (
        'column',
        'dest_table',
        'dest_column',
        'table'))

View = namedtuple(
    'View', (
        'name',
        'sql'))

# Used by Connection.table_column_metadata - slightly different output from the
# Connection.get_columns() output.
ColumnMetadata = namedtuple(
    'ColumnMetadata', (
        'table',
        'column',
        'datatype',
        'collation',
        'not_null',
        'primary_key',
        'auto_increment'))
