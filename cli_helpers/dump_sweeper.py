# WikECD/cli_helpers/dump_sweeper.py
from __future__ import annotations
import os
import csv
import json
import time
import traceback
from typing import Dict, List, Iterable, Tuple

from ..sources.dump_utils import (
    index_dump_dir,
    find_files_covering_ids,
    save_index,
    load_index,
)
from ..sources.xml_parser import get_revisions_from_file
from ..compression.compressor import compress_article
from ..storage.serializer import save
from ..logger import get_logger

from concurrent.futures import ProcessPoolExecutor, as_completed

logger = get_logger("WikECD.dump_sweeper")


def _compute_manifest_row(
    title: str,
    pid: int,
    source_file: str,
    out_path: str,
    revs_len: int,
    article,
    t0: float,
    t1: float,
) -> Dict:
    """
    Create a manifest row with some helpful metrics.
    """
    row = {
        "title": title,
        "page_id": pid,
        "source_file": os.path.basename(source_file),
        "artifact": out_path,
        "revisions": revs_len,
        "anchors": len(getattr(article, "anchors", []) or []),
        "partitions": len(article.meta.get("partitions", [])) if getattr(article, "meta", None) else None,
        "solver": getattr(article, "meta", {}).get("solver"),
        "strategy": getattr(article, "meta", {}).get("strategy"),
        "time_budget": getattr(article, "meta", {}).get("time_budget"),
        "compress_seconds": round(t1 - t0, 3),
    }
    # optional: space-related metrics if your compressor populates them
    if getattr(article, "meta", None):
        if "space_cost" in article.meta:
            row["space_cost"] = article.meta["space_cost"]
        if "time_cost" in article.meta:
            row["time_cost"] = article.meta["time_cost"]
    return row


def _get_out_path_for_pid(out_dir: str, pid: int) -> str:
    # consistent artifact naming
    return os.path.join(out_dir, f"page_{pid}.comp.gz")


def _work_file(args_tuple):
    """
    Worker process: handle one bz2 file for one or more page_ids.
    It will use fast indexed path if 'use_fast' is True and an index is available,
    otherwise it falls back to streaming.
    Returns: list of manifest rows.
    """
    (
        fp,
        pids,
        solver,
        strategy,
        eps,
        assume_sorted,
        max_pages_scan,
        out_dir,
        use_fast,
        index_path_for_file,
        force,
    ) = args_tuple

    rows: List[Dict] = []

    try:
        # lazy imports inside the worker to keep the parent fast/light
        from ..sources.fast_page_reader import iter_revisions_fast  # fast seek
        from ..sources.xml_parser import get_revisions_from_file    # streaming
        from ..compression.compressor import compress_article
        from ..storage.serializer import save

        for pid in pids:
            out_path = _get_out_path_for_pid(out_dir, pid)
            if (not force) and os.path.exists(out_path):
                # skip existing artifact
                rows.append({
                    "title": f"page_{pid}",
                    "page_id": pid,
                    "source_file": os.path.basename(fp),
                    "artifact": out_path,
                    "revisions": None,
                    "anchors": None,
                    "partitions": None,
                    "skipped": True
                })
                continue

            # choose fast vs streaming
            if use_fast and index_path_for_file and os.path.exists(index_path_for_file):
                revs = list(iter_revisions_fast(fp, index_path_for_file, pid))
            else:
                revs = list(get_revisions_from_file(
                    fp,
                    page_ids={pid},
                    assume_sorted=assume_sorted,
                    progress=True,
                    progress_interval=250,
                    max_pages_scan=max_pages_scan
                ))

            if not revs:
                rows.append({
                    "title": f"page_{pid}",
                    "page_id": pid,
                    "source_file": os.path.basename(fp),
                    "artifact": None,
                    "revisions": 0,
                    "warning": "No revisions found in file"
                })
                continue

            # compress
            title = f"page_{pid}"
            t0 = time.time()
            article = compress_article(title, revs, solver=solver, strategy=strategy, eps=eps)
            texts = [r.text for r in revs]
            base_texts = {b: texts[b] for b in getattr(article, "anchors", [])}
            save(out_path, article, base_texts)
            t1 = time.time()

            rows.append(_compute_manifest_row(
                title=title,
                pid=pid,
                source_file=fp,
                out_path=out_path,
                revs_len=len(revs),
                article=article,
                t0=t0,
                t1=t1
            ))

    except Exception:
        rows.append({
            "error_file": os.path.basename(fp),
            "error": traceback.format_exc()
        })

    return rows


def extract_from_dump_dir(
    dump_dir: str,
    page_ids: List[int],
    out_dir: str,
    index_path: str = None,
    pattern: str = "*pages-meta-history*.xml.bz2",  # bz2-only default
    solver: str = "heuristic",
    strategy: str = "fptas",
    eps: float = 0.1,
    assume_sorted: bool = True,
    max_pages_scan: int = None,
    verbose: bool = False,
    jobs: int = 1,
    resume: bool = True,
    force: bool = False,
    auto_index: bool = False
):
    """
    Orchestrates extraction for a set of page_ids from a local dump directory.

    - Builds/loads a file->(start,end) index (filename ranges).
    - Maps page_ids to the first matching file.
    - (Optional) Auto-builds a seek index per bz2 (file.pageidx.sqlite).
    - Parallelizes work by file with ProcessPoolExecutor.
    - Respects resume/force flags.
    - Emits manifest.json and manifest.csv.
    """
    os.makedirs(out_dir, exist_ok=True)

    # 1) Load or build the filename-range index for the dump directory
    if index_path and os.path.exists(index_path):
        idx = load_index(index_path)
        if verbose:
            logger.info("Loaded index with %d files from %s", len(idx), index_path)
    else:
        idx = index_dump_dir(dump_dir, pattern=pattern)
        if index_path:
            save_index(idx, index_path)
            if verbose:
                logger.info("Indexed %d files under %s (pattern=%s) -> %s", len(idx), dump_dir, pattern, index_path)

    if not idx:
        logger.warning("Index is empty. Check dump_dir='%s' and pattern='%s'", dump_dir, pattern)
        # still write empty manifests for consistency
        _write_manifests(out_dir, [])
        return

    # 2) Map each pid -> list of files that could contain it; pick the first
    file_map: Dict[int, List[str]] = find_files_covering_ids(idx, page_ids)
    file_to_pids: Dict[str, List[int]] = {}
    for pid, files in file_map.items():
        if not files:
            logger.warning("No local dump files cover pid=%s", pid)
            continue
        fp = files[0]
        file_to_pids.setdefault(fp, []).append(pid)

    if not file_to_pids:
        logger.info("No matching files for requested page_ids. Writing empty manifest.")
        _write_manifests(out_dir, [])
        return

    # 3) Auto-index per bz2 (fast seek) if requested
    #    Each bz2 file gets a 'file.pageidx.sqlite' alongside it.
    use_fast_by_file: Dict[str, Tuple[bool, str]] = {}
    if auto_index:
        try:
            from ..sources.bz2_page_index import build_page_index
        except Exception as e:
            logger.warning("Auto-index requested but indexer unavailable: %s", e)
            auto_index = False

    for fp in file_to_pids.keys():
        index_sqlite = fp + ".pageidx.sqlite"
        if auto_index:
            if not os.path.exists(index_sqlite):
                logger.info("Auto-indexing %s ...", os.path.basename(fp))
                try:
                    n = build_page_index(fp, index_sqlite)
                    logger.info("Indexed %d pages -> %s", n, os.path.basename(index_sqlite))
                except Exception as e:
                    logger.warning("Index build failed for %s: %s", os.path.basename(fp), e)
                    index_sqlite = None
        use_fast_by_file[fp] = (index_sqlite is not None and os.path.exists(index_sqlite), index_sqlite)

    # 4) Build tasks (grouped per file). Apply resume/force filtering here.
    tasks: List[Tuple] = []
    total_targets = 0
    for fp, pids in file_to_pids.items():
        # Apply resume/force per-pid
        target_pids = []
        for pid in pids:
            out_path = _get_out_path_for_pid(out_dir, pid)
            if resume and (not force) and os.path.exists(out_path):
                if verbose:
                    logger.info("Skipping existing artifact: %s", out_path)
                continue
            target_pids.append(pid)
        if not target_pids:
            continue
        total_targets += len(target_pids)

        use_fast, idx_sqlite = use_fast_by_file.get(fp, (False, None))
        tasks.append((
            fp,
            target_pids,
            solver,
            strategy,
            eps,
            assume_sorted,
            max_pages_scan,
            out_dir,
            use_fast,
            idx_sqlite,
            force,
        ))

    if not tasks:
        logger.info("Nothing to do (all requested pages already exist or no matches).")
        _write_manifests(out_dir, [])
        return

    # 5) Execute tasks (parallel by file)
    manifest_rows: List[Dict] = []
    if jobs and jobs > 1:
        if verbose:
            logger.info("Running with %d worker(s) across %d target page(s)", jobs, total_targets)
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = [ex.submit(_work_file, t) for t in tasks]
            for fut in as_completed(futs):
                res = fut.result()
                if res:
                    manifest_rows.extend(res)
    else:
        if verbose:
            logger.info("Running single-process across %d target page(s)", total_targets)
        for t in tasks:
            manifest_rows.extend(_work_file(t))

    # 6) Write manifests
    _write_manifests(out_dir, manifest_rows)


def _write_manifests(out_dir: str, rows: List[Dict]):
    """
    Write manifest.json and manifest.csv using the union of keys for CSV header.
    """
    manifest_json = os.path.join(out_dir, "manifest.json")
    manifest_csv = os.path.join(out_dir, "manifest.csv")

    # JSON
    with open(manifest_json, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)

    # CSV with a stable header
    header = set()
    for r in rows:
        header.update(r.keys())
    header = list(sorted(header)) if header else ["page_id", "title", "source_file", "artifact", "revisions"]

    with open(manifest_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    logger.info("Manifest written: %s", manifest_json)
    logger.info("Manifest written: %s", manifest_csv)
