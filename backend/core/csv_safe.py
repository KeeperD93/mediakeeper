"""CSV cell sanitiser to neutralise spreadsheet formula injection.

Spreadsheet apps (Excel, LibreOffice, Google Sheets) interpret a cell
that begins with ``=``, ``+``, ``-``, ``@``, tab, CR or LF as a formula.
A user-controlled string in an exported CSV (display name, list title,
note) can therefore execute arbitrary formulas on the admin's machine
when they open the file.

The fix recommended by OWASP is to prefix any such cell with a single
quote so the spreadsheet renders the literal text instead of evaluating
it. The original payload remains intact for any non-spreadsheet
consumer (text editor, Python ``csv`` reader, etc.).
"""
from __future__ import annotations

_DANGEROUS_LEADERS = ("=", "+", "-", "@", "\t", "\r", "\n")


def safe_csv_cell(value: object) -> object:
    """Neutralise a single CSV cell against formula injection.

    Non-strings are returned untouched so numeric/boolean columns keep
    their native type. Strings whose first non-whitespace character is
    a spreadsheet formula leader get a leading apostrophe.
    """
    if not isinstance(value, str):
        return value
    stripped = value.lstrip(" ")
    if stripped and stripped[0] in _DANGEROUS_LEADERS:
        return "'" + value
    return value


def safe_csv_row(row: list) -> list:
    """Apply :func:`safe_csv_cell` to every cell of a row."""
    return [safe_csv_cell(cell) for cell in row]
