#!/usr/bin/env python

import os
import re
import sys


COMMENT = re.compile('/\*(.+?)\*/')
SIMPLE_CONSTANT = re.compile('\s*#define SQLITE_(\w+?)\s+([^\s]+)'
                             '(?:\s+/\*(.+?)\*/)?')
SQLITE_API = 'SQLITE_API '


def main(filename):
    with open(filename) as fh:
        lines = [l.strip() for l in fh.read().splitlines() if l.strip()]

    defines = []

    # First let's translate all the simple constants.
    for line in lines:
        match_obj = SIMPLE_CONSTANT.match(line)
        if match_obj is not None:
            name, val, comment = match_obj.groups()
            cy = 'cdef SQLITE_%s = %s' % (name, val)
            if comment:
                cy += '  # %s' % comment.strip()
            defines.append(cy)

    print('\n'.join(defines))

    # Now let's translate the functions.
    funcs = []
    curr_func = []
    in_func = False
    for line in lines:
        # First remove all comments.
        line = COMMENT.sub('', line)

        endline = ';' in line
        line = line.split(';', 1)[0]

        if line.startswith(SQLITE_API):
            clean = line[len(SQLITE_API):].strip()
            if endline:
                funcs.append('cdef %s' % clean)
            else:
                curr_func.append(clean)
                in_func = True
        elif in_func:
            if line.startswith(SQLITE_API):
                raise ValueError('Should not see another API decl here.')

            curr_func.append(line.strip())
            if endline:
                funcs.append('cdef %s' % ' '.join(curr_func))
                curr_func = []
                in_func = False


    if in_func and curr_func:
        funcs.append('cdef %s' % ''.join(curr_func))

    print('\n\n')
    print('\n'.join(funcs))


def die(s):
    sys.stderr.write(s)
    sys.stderr.flush()
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sqlite3h = os.path.join(os.environ['HOME'], 'code/sqlite/sqlite3.h')
    elif len(sys.argv) == 2:
        sqlite3h = sys.argv[1]
    else:
        die('please specify path to sqlite3.h\r\n')

    if not os.path.exists(sqlite3h):
        die('sqlite3 header "%s" not found\r\n' % sqlite3h)

    main(sqlite3h)
