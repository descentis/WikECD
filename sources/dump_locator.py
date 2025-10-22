from __future__ import annotations
import re, os, pathlib, requests
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple, Optional

META_HISTORY_RE = re.compile(
    r'href="(?P<fname>enwiki-\d{8}-pages-meta-history(?P<part>\d+)\.xml-p(?P<start>\d+)p(?P<end>\d+)\.bz2)"'
)


@dataclass(frozen=True)
class DumpPart:
    url: str
    start: int
    end: int
    part: int
    fname: str


def list_meta_history_parts(dump_url: str) -> List[DumpPart]:
    """Parse the dump directory HTML and list pages-meta-history parts with id ranges."""
    if not dump_url.endswith("/"):
        dump_url += "/"
    resp = requests.get(dump_url, timeout=120)
    resp.raise_for_status()
    parts: List[DumpPart] = []
    for m in META_HISTORY_RE.finditer(resp.text):
        fname = m.group("fname")
        start = int(m.group("start"))
        end   = int(m.group("end"))
        part  = int(m.group("part"))
        parts.append(DumpPart(
            url=dump_url + fname, start=start, end=end, part=part, fname=fname
        ))
    # sort by (part, start)
    parts.sort(key=lambda x: (x.part, x.start))
    return parts


def pick_parts_for_pageids(parts: List[DumpPart], page_ids: Iterable[int]) -> Dict[int, DumpPart]:
    """Map each page_id to the single DumpPart whose [start,end] contains it."""
    result: Dict[int, DumpPart] = {}
    for pid in page_ids:
        # binary search would be nicer; linear is fine given the list isn’t huge per part
        hit = next((p for p in parts if p.start <= pid <= p.end), None)
        if hit:
            result[pid] = hit
    return result


def ensure_download(url: str, dest_dir: str) -> str:
    """Download a file to dest_dir if missing; stream to disk. Returns local path."""
    pathlib.Path(dest_dir).mkdir(parents=True, exist_ok=True)
    fname = url.rsplit("/", 1)[-1]
    out_path = os.path.join(dest_dir, fname)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return out_path
