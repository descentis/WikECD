# WikECD/sources/bz2_page_index.py
from __future__ import annotations
import re, sqlite3
from typing import Optional
import indexed_bzip2

# byte tokens
PAGE_OPEN  = b"<page>"
ID_OPEN    = b"<id>"
ID_CLOSE   = b"</id>"
REV_OPEN   = b"<revision>"

CHUNK = 1 << 20  # 1 MiB

def _ensure_schema(db: sqlite3.Connection):
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS page_index (
        page_id INTEGER PRIMARY KEY,
        uoffset INTEGER NOT NULL
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_page_uoffset ON page_index(uoffset)")
    db.commit()

def build_page_index(bz2_path: str, index_sqlite: str) -> int:
    """
    One-time linear scan: record (page_id, uncompressed_offset_of_<page>).
    Uses a streaming buffer to find '<page>', then peeks a small window
    to read page-level <id> that appears BEFORE the first <revision>.
    Returns the number of indexed pages.
    """
    db = sqlite3.connect(index_sqlite)
    _ensure_schema(db)
    cur = db.cursor()

    f = indexed_bzip2.open(bz2_path)  # seekable bz2
    buf = b""
    base_off = 0  # uncompressed offset corresponding to buf[0]
    total = 0

    while True:
        chunk = f.read(CHUNK)
        if not chunk:
            break
        buf += chunk

        start = 0
        while True:
            pos = buf.find(PAGE_OPEN, start)
            if pos == -1:
                break

            page_uoff = base_off + pos  # absolute uncompressed offset of '<page>'
            pid = _peek_page_id(f, page_uoff)
            if pid is not None:
                cur.execute(
                    "INSERT OR REPLACE INTO page_index(page_id, uoffset) VALUES (?, ?)",
                    (int(pid), int(page_uoff))
                )
                total += 1

            # continue searching
            start = pos + len(PAGE_OPEN)

        # keep a small tail so tokens split across chunks are still found
        tail_keep = max(len(PAGE_OPEN), len(ID_OPEN), len(REV_OPEN)) - 1
        if len(buf) > tail_keep:
            base_off += len(buf) - tail_keep
            buf = buf[-tail_keep:]

    db.commit()
    db.close()
    f.close()
    return total

def _peek_page_id(f: indexed_bzip2.IndexedBzip2File, page_uoff: int) -> Optional[int]:
    """
    Lightweight peek: seek to '<page>' start, read a small window (e.g. 64–128KB),
    and extract the *page-level* <id> that appears BEFORE the first <revision>.
    This avoids reading the whole page or waiting for '</page>'.
    Restores the original file position so the outer scan stays in sync.
    """
    # Save current streaming position and restore after peek
    try:
        cur_pos = f.tell()
    except Exception:
        cur_pos = None

    try:
        f.seek(page_uoff)
        window = f.read(128 * 1024)  # usually enough for <title><ns><id>…<revision>

        # Find the first <revision> boundary (if any) so we only search header
        rev_pos = window.find(REV_OPEN)
        header = window if rev_pos == -1 else window[:rev_pos]

        # Find first <id>..</id> in the header
        id_start = header.find(ID_OPEN)
        if id_start == -1:
            return None
        id_start += len(ID_OPEN)
        id_end = header.find(ID_CLOSE, id_start)
        if id_end == -1:
            return None

        # Extract and parse integer
        try:
            pid = int(header[id_start:id_end].strip())
            return pid
        except Exception:
            return None
    finally:
        # restore streaming position so the main loop continues correctly
        if cur_pos is not None:
            f.seek(cur_pos)

def lookup_offset(index_sqlite: str, page_id: int) -> Optional[int]:
    db = sqlite3.connect(index_sqlite)
    cur = db.cursor()
    cur.execute("SELECT uoffset FROM page_index WHERE page_id=?", (int(page_id),))
    row = cur.fetchone()
    db.close()
    return int(row[0]) if row else None
