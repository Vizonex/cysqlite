cimport cython


@cython.freelist(128)
cdef class Buffer(object):
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

    @staticmethod
    cdef Buffer from_object(obj):
        cdef Buffer buf
        buf = Buffer.__new__(Buffer)
        return buf
