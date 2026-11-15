"""Split a .sql script into statements.

Understands quotes, backticks, -- / # / block comments and the mysql-client
`DELIMITER` command, so trigger bodies containing ';' are kept in one piece.
"""
from __future__ import annotations


def split_sql(script: str) -> list[str]:
    statements: list[str] = []
    delimiter = ";"
    buf: list[str] = []
    i, n = 0, len(script)
    at_line_start = True

    def flush() -> None:
        stmt = "".join(buf).strip()
        buf.clear()
        if stmt:
            statements.append(stmt)

    while i < n:
        ch = script[i]

        # DELIMITER command (only at the start of a line, outside any statement text)
        if at_line_start and script[i:i + 9].upper() == "DELIMITER" and (i + 9 >= n or script[i + 9] in " \t"):
            end = script.find("\n", i)
            end = n if end == -1 else end
            new_delim = script[i + 9:end].strip()
            if new_delim:
                if "".join(buf).strip():
                    flush()
                delimiter = new_delim
            i = end + 1
            at_line_start = True
            continue

        if ch in " \t\r":
            buf.append(ch)
            i += 1
            continue
        if ch == "\n":
            buf.append(ch)
            i += 1
            at_line_start = True
            continue
        at_line_start = False

        # comments
        if script.startswith("--", i) and (i + 2 >= n or script[i + 2] in " \t\r\n"):
            end = script.find("\n", i)
            i = n if end == -1 else end
            continue
        if ch == "#":
            end = script.find("\n", i)
            i = n if end == -1 else end
            continue
        if script.startswith("/*", i):
            end = script.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue

        # quoted text
        if ch in ("'", '"', "`"):
            quote = ch
            buf.append(ch)
            i += 1
            while i < n:
                c = script[i]
                buf.append(c)
                i += 1
                if c == "\\" and quote != "`" and i < n:
                    buf.append(script[i])
                    i += 1
                elif c == quote:
                    if i < n and script[i] == quote:  # doubled quote = escaped quote
                        buf.append(script[i])
                        i += 1
                    else:
                        break
            continue

        if script.startswith(delimiter, i):
            flush()
            i += len(delimiter)
            continue

        buf.append(ch)
        i += 1

    flush()
    return statements
