from __future__ import annotations
import os, re, json, pathlib, requests
from dataclasses import dataclass
from typing import Iterable, List, Dict, Optional

try:
    from tqdm import tqdm
except Exception:
    tqdm = None  # graceful fallback

# VERY permissive HTML matcher: just look for the filename anywhere in the page text.
ANYWHERE_FILE_RE = re.compile(
    r'(enwiki-\d{8}-pages-meta-history[^"\s<>]*?\.xml-p(?P<start>\d+)p(?P<end>\d+)\.(?P<ext>bz2|7z))',
    re.IGNORECASE
)

@dataclass(frozen=True)
class DumpPart:
    url: str
    start: int
    end: int
    part: int  # may be 0 if absent
    fname: str
    ext: str

def _normalize(url: str) -> str:
    return url if url.endswith("/") else url + "/"

def _session(user_agent: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent or "WikECD/0.1 (+contact: you@example.com)"
    })
    return s

def _from_dumpstatus_json(s: requests.Session, dump_url: str, verbose: bool) -> List[DumpPart]:
    dump_url = _normalize(dump_url)
    url = dump_url + "dumpstatus.json"
    r = s.get(url, timeout=120)
    if verbose:
        print(f"[WikECD] GET {url} -> {r.status_code}, {len(r.content)} bytes")
    if r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    job = (data.get("jobs") or {}).get("pages-meta-history")
    if not job:
        return []
    files = job.get("files") or {}
    parts: List[DumpPart] = []
    for fname in files.keys():
        m = re.search(r"pages-meta-history(?P<part>\d*)\.xml-p(?P<start>\d+)p(?P<end>\d+)\.(?P<ext>bz2|7z)$", fname, re.I)
        if not m:
            continue
        part = int(m.group("part")) if m.group("part") else 0
        parts.append(DumpPart(
            url=_normalize(dump_url) + fname,
            start=int(m.group("start")),
            end=int(m.group("end")),
            part=part,
            fname=fname,
            ext=m.group("ext").lower()
        ))
    parts.sort(key=lambda x: (x.part, x.start))
    return parts

def _from_html(s: requests.Session, dump_url: str, verbose: bool) -> List[DumpPart]:
    dump_url = _normalize(dump_url)
    r = s.get(dump_url, timeout=120)
    if verbose:
        snippet = r.text[:400].replace("\n"," ")
        print(f"[WikECD] GET {dump_url} -> {r.status_code}, {len(r.content)} bytes; head: {snippet!r}")
    if r.status_code != 200:
        return []
    text = r.text
    parts: List[DumpPart] = []
    for m in ANYWHERE_FILE_RE.finditer(text):
        fname = m.group(1)
        # try to extract optional part number
        pm = re.search(r"pages-meta-history(?P<part>\d*)\.xml", fname, re.I)
        part = int(pm.group("part")) if pm and pm.group("part") else 0
        parts.append(DumpPart(
            url=dump_url + fname,
            start=int(m.group("start")),
            end=int(m.group("end")),
            part=part,
            fname=fname,
            ext=m.group("ext").lower(),
        ))
    parts.sort(key=lambda x: (x.part, x.start))
    return parts

def list_meta_history_parts(dump_url: str, user_agent: Optional[str] = None, allow_latest_fallback: bool = True, verbose: bool = False) -> List[DumpPart]:
    s = _session(user_agent)
    dump_url = _normalize(dump_url)

    parts = _from_dumpstatus_json(s, dump_url, verbose)
    if not parts:
        parts = _from_html(s, dump_url, verbose)

    if not parts and allow_latest_fallback:
        base = dump_url.rstrip("/")
        segs = base.split("/")
        if segs[-1].isdigit():
            latest_url = "/".join(segs[:-1] + ["latest"]) + "/"
            alt = _from_dumpstatus_json(s, latest_url, verbose) or _from_html(s, latest_url, verbose)
            if alt:
                print(f"[WikECD] No pages-meta-history parts at {dump_url}. Falling back to {latest_url}")
                parts = alt

    if verbose:
        print(f"[WikECD] list_meta_history_parts: found {len(parts)} part(s) for {dump_url}")
        for p in parts[:10]:
            print(f"  - {p.fname} [{p.start}-{p.end}]")

    if not parts:
        print(f"[WikECD] No pages-meta-history parts found for {dump_url} (and no latest fallback).")
    return parts

def pick_parts_for_pageids(parts: List[DumpPart], page_ids: Iterable[int]) -> Dict[int, DumpPart]:
    result: Dict[int, DumpPart] = {}
    for pid in page_ids:
        hit = next((p for p in parts if p.start <= pid <= p.end), None)
        if hit:
            result[pid] = hit
    return result

def ensure_download(url: str, dest_dir: str, user_agent: Optional[str] = None) -> str:
    pathlib.Path(dest_dir).mkdir(parents=True, exist_ok=True)
    fname = url.rsplit("/", 1)[-1]
    out_path = os.path.join(dest_dir, fname)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return out_path

    s = _session(user_agent)
    with s.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        bar = None
        if tqdm:
            bar = tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=f"Downloading {fname}")
        try:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        if bar:
                            bar.update(len(chunk))
        finally:
            if bar:
                bar.close()
    return out_path
