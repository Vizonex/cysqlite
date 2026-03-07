import logging

from cysqlite import SQLITE_TRACE_PROFILE


def slow_query_log(conn, threshold_ms=50, logger=None, level=logging.WARNING,
                   expand_sql=True):
    log = logging.getLogger(logger or __name__)
    def trace(event, sid, sql, ns):
        if not sql:
            return
        ms = ns / 1000000
        if ms >= threshold_ms:
            log.log(level, 'Slow query %0.1fms: %s', ms, sql)

    conn.trace(trace, SQLITE_TRACE_PROFILE, expand_sql=expand_sql)
    return True
