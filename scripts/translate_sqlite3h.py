#!/usr/bin/env python

import optparse
import os
import re
import sys


COMMENT = re.compile(r'/\*(.+?)\*/')
SIMPLE_CONSTANT = re.compile(r'\s*#define SQLITE_(\w+?)\s+(.+)'
                             r'(?:/\*(.+?)\*/)?')
SQLITE_API = 'SQLITE_API '

KNOWN = re.compile(r'cdef int SQLITE_([^\s]+)')


def main(filename, constants=False):
    defines = []
    const_list = []
    known = set()

    if constants:
        # Read known constants from our include file.
        curdir = os.path.dirname(__file__)
        with open(os.path.join(os.path.dirname(curdir), 'src/sqlite3.pxi')) as fh:
            lines = [l.strip() for l in fh.read().splitlines() if l.strip()]
        for line in lines:
            match_obj = KNOWN.match(line)
            if match_obj is not None:
                known.add(match_obj.groups()[0])

    with open(filename) as fh:
        lines = [l.strip() for l in fh.read().splitlines() if l.strip()]

    # First let's translate all the simple constants.
    for line in lines:
        match_obj = SIMPLE_CONSTANT.match(line)
        if match_obj is not None:
            name, val, comment = match_obj.groups()
            cy = 'cdef SQLITE_%s = %s' % (name, val)
            const = 'C_SQLITE_%s = SQLITE_%s  # %s' % (name, name, val)
            if comment:
                cy += '  # %s' % comment.strip()
                const += ' %s' % comment.strip()
            defines.append(cy)
            if name in known:
                const_list.append(const)
            else:
                print(name)

    if constants:
        print('\n'.join(const_list))
        return
    else:
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
    parser = optparse.OptionParser()
    parser.add_option('-c', '--constants', action='store_true', dest='constants',
                      help='Only output constants for inclusion in a PXD.')

    options, args = parser.parse_args()

    if len(args) == 0:
        sqlite3h = os.path.join(os.environ['HOME'], 'code/sqlite/sqlite3.h')
    elif len(sys.argv) == 1:
        sqlite3h = args[1]
    else:
        die('please specify path to sqlite3.h\r\n')

    if not os.path.exists(sqlite3h):
        die('sqlite3 header "%s" not found\r\n' % sqlite3h)

    main(sqlite3h, options.constants)
