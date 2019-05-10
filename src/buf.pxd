cdef class Buffer:
    cdef:
        const char *data
        Py_ssize_t length
        long _hash

    cdef get_hash(self)

    @staticmethod
    cdef Buffer from_object(obj)
