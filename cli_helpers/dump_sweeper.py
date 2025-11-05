# WikECD/cli_helpers/dump_sweeper.py
import os
import csv
import json
from typing import List
from ..sources.dump_utils import index_dump_dir, find_files_covering_ids, save_index, load_index
from ..sources.xml_parser import get_revisions_from_file
from ..compression.compressor import compress_article
from ..storage.serializer import save  # your existing save()
from ..logger import get_logger

logger = get_logger("WikECD.dump_sweeper")


def extract_from_dump_dir(
    dump_dir: str,
    page_ids: List[int],
    out_dir: str,
    index_path: str = None,
    pattern: str = "enwiki-*-pages-meta-history*.xml.*",
    solver: str = "heuristic",
    strategy: str = "fptas",
    eps: float = 0.1,
    assume_sorted: bool = True,
    max_pages_scan: int = None,
    verbose: bool = False,
):
    os.makedirs(out_dir, exist_ok=True)
    # load or create index
    if index_path and os.path.exists(index_path):
        idx = load_index(index_path)
    else:
        idx = index_dump_dir(dump_dir, pattern=pattern)
        if index_path:
            save_index(idx, index_path)

    mapping = find_files_covering_ids(idx, page_ids)
    manifest = []
    for pid, files in mapping.items():
        if not files:
            logger.warning("No local dump files cover pid=%s", pid)
            continue
        # prefer first file (they're sorted in index_dump_dir)
        fp = files[0]
        logger.info("Processing pid=%s from %s", pid, os.path.basename(fp))
        revs_iter = get_revisions_from_file(
            fp,
            page_ids={pid},
            assume_sorted=assume_sorted,
            progress=True,
            progress_interval=250,
            max_pages_scan=max_pages_scan
        )
        revs = list(revs_iter)
        if not revs:
            logger.warning("No revisions found for pid=%s in %s", pid, os.path.basename(fp))
            continue
        # compress article
        title = revs[0].revid if hasattr(revs[0], 'title') and revs[0].title else f"page_{pid}"
        article = compress_article(title, revs, solver=solver, strategy=strategy, eps=eps)
        out_path = os.path.join(out_dir, f"page_{pid}.comp.gz")
        # base_texts (we expect article.base_texts populated by compressor)
        base_texts = getattr(article, "base_texts", None)
        save(out_path, article, base_texts)
        logger.info("Saved compressed article %s -> %s", pid, out_path)
        manifest.append({
            "page_id": pid,
            "title": title,
            "source_file": fp,
            "out_path": out_path,
            "revisions": len(revs),
        })

    # write manifest JSON + CSV
    manifest_json = os.path.join(out_dir, "manifest.json")
    with open(manifest_json, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    manifest_csv = os.path.join(out_dir, "manifest.csv")
    with open(manifest_csv, "w", encoding="utf-8", newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=["page_id","title","source_file","out_path","revisions"])
        writer.writeheader()
        for row in manifest:
            writer.writerow(row)
    logger.info("Manifest written: %s", manifest_json)
    logger.info("Manifest written: %s", manifest_csv)
