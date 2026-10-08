"""content-engine import fix: UTF-8 text I/O on Windows.

Python on Windows (without UTF-8 mode) opens text files in the ANSI code page (cp1252),
which silently mangles Swedish transcripts (å ä ö) when a script reads or writes JSON.
Every kit script imports this first; on other platforms, or with PYTHONUTF8=1, it does nothing.
"""
import builtins
import io
import sys

if sys.platform == "win32" and not sys.flags.utf8_mode:
    _open = builtins.open

    def _utf8_open(file, mode="r", buffering=-1, encoding=None, *args, **kwargs):
        if "b" not in mode and encoding is None:
            encoding = "utf-8"
        return _open(file, mode, buffering, encoding, *args, **kwargs)

    builtins.open = _utf8_open
    io.text_encoding = lambda encoding, stacklevel=2: encoding if encoding is not None else "utf-8"
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
