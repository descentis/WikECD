# WikECD/sources/fast_page_reader.py
from __future__ import annotations
from typing import Iterable, Optional
import indexed_bzip2
from lxml import etree
from .base import Revision
from .bz2_page_index import lookup_offset

PAGE_CLOSE = b"</page>"


def iter_revisions_fast(bz2_path: str, index_sqlite: str, page_id: int) -> Iterable[Revision]:
    uoff = lookup_offset(index_sqlite, page_id)
    if uoff is None:
        return  # not in this file
    f = indexed_bzip2.open(bz2_path)
    f.seek(uoff)
    # read until the end of this page
    buf = bytearray()
    while True:
        chunk = f.read(64 * 1024)
        if not chunk:
            break
        buf += chunk
        pos = buf.find(PAGE_CLOSE)
        if pos != -1:
            buf = buf[:pos + len(PAGE_CLOSE)]
            break
    f.close()

    xml = b"<root>" + bytes(buf) + b"</root>"
    root = etree.fromstring(xml)
    page = root.find("page") or root.find("{*}page")
    if page is None:
        return
    ns = "{*}"
    for rev in page.findall("./revision") or page.findall(f"./{ns}revision"):
        rid_el = rev.find("./id") or rev.find(f"./{ns}id")
        ts_el  = rev.find("./timestamp") or rev.find(f"./{ns}timestamp")
        txt_el = rev.find("./text") or rev.find(f"./{ns}text")
        try:
            revid = int(rid_el.text) if rid_el is not None and rid_el.text else -1
        except Exception:
            revid = -1
        ts = ts_el.text if ts_el is not None else ""
        text = txt_el.text or "" if txt_el is not None else ""
        yield Revision(revid=revid, timestamp=ts, text=text)
