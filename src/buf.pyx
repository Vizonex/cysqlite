cimport cython
from cpython.bytes cimport PyBytes_AS_STRING
from cpython.bytes cimport PyBytes_Check
from cpython.object cimport Py_EQ
from cpython.ref cimport Py_DECREF
from cpython.ref cimport Py_INCREF
from libc.string cimport memcmp


@cython.freelist(128)
cdef class Buffer(object):
    cdef:
        const char *data
        Py_ssize_t length
        long _hash

    def __cinit__(self):
        self.data = NULL
        self.length = 0
        self._hash = -1

    def __richcmp__(self, other, int op):
        if op != Py_EQ:
            raise ValueError('only equality tests are permitted')

        cdef Buffer lhs = <Buffer>self
        cdef Buffer rhs = <Buffer>other

        if lhs.length != rhs.length or lhs._hash != rhs._hash:
            return False

        if lhs.data == rhs.data:
            return True

        return memcmp(<const void *>lhs.data, <const void *>rhs.data, lhs.length) == 0

    cdef get_hash(self):
        cdef:
            long h
            unsigned char *p
            Py_ssize_t n

        if self._hash != -1:
            return self._hash

        p = <unsigned char *>self.data
        n = self.length
        h = p[0] << 7

        while n:
            n -= 1
            p += 1
            h = (1000003 * h) ^ p[0]

        h ^= self.length
        h += 1
        if h == -1:
            h -= 1

        self._hash = h
        return self._hash

    def hash(self):
        return self.get_hash()

    @classmethod
    def make(cls, data):
        return buffer_from_object(data, 0, len(data))


cdef Buffer buffer_from_object(obj, Py_ssize_t offset, Py_ssize_t n):
    cdef:
        Buffer buf = Buffer.__new__(Buffer)
        Buffer src

    if isinstance(obj, Buffer):
        src = <Buffer>obj
        buf.data = src.data + offset
        buf.length = n
        buf._hash = -1
        Py_INCREF(obj)
        return buf

    if not PyBytes_Check(obj):
        raise TypeError('must be bytes or Buffer()')

    cdef char *d = PyBytes_AS_STRING(<bytes>obj)
    Py_INCREF(obj)
    buf.data = d + offset
    buf.length = n
    buf._hash = -1
    return buf
