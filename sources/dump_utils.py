# WikECD/sources/dump_utils.py
import re
import os
import json
from typing import List, Tuple, Optional, Dict

FNAME_RX = re.compile(r'p(\d+)p(\d+)')  # matches p<start>p<end> in filenames


def parse_range_from_filename(fname: str) -> Optional[Tuple[int,int]]:
    """
    Parse page-id range from a dump filename.
    Returns (start, end) if found, else None.
    """
    m = FNAME_RX.search(fname)
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2))
    return (lo, hi)


def index_dump_dir(dirpath: str, pattern: str = "*.bz2") -> Dict[str, Tuple[int,int]]:
    """
    Scan a directory and return mapping {filepath: (start, end)} for files
    that match the pattern and contain a parseable p<start>p<end> segment.
    """
    import glob
    mapping = {}
    files = sorted(glob.glob(os.path.join(dirpath, pattern)))
    for fp in files:
        b = os.path.basename(fp)
        rng = parse_range_from_filename(b)
        if rng:
            mapping[fp] = rng
    return mapping


def find_files_covering_ids(index_map: Dict[str, Tuple[int,int]], page_ids: List[int]) -> Dict[int, List[str]]:
    """
    Return mapping page_id -> [files that contain it].
    """
    out = {pid: [] for pid in page_ids}
    for fp, (lo, hi) in index_map.items():
        for pid in page_ids:
            if lo <= pid <= hi:
                out[pid].append(fp)
    return out


def save_index(index_map: Dict[str, Tuple[int,int]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({k: [v[0], v[1]] for k,v in index_map.items()}, fh, indent=2)


def load_index(path: str) -> Dict[str, Tuple[int,int]]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: (int(v[0]), int(v[1])) for k,v in raw.items()}
