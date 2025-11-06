# WikECD/analytics/analyze.py
from __future__ import annotations
import os, glob, math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import statistics as stats

from ..storage.serializer import load

@dataclass
class ArtifactMetrics:
    artifact: str
    title: Optional[str]
    page_id: Optional[int]
    n_revisions: int
    n_anchors: int
    n_partitions: int
    avg_chain_len: float
    max_chain_len: int
    space_cost: Optional[int]
    time_cost: Optional[int]
    orig_size: Optional[int]
    compression_ratio: Optional[float]       # space_cost / orig_size
    anchor_density: Optional[float]          # n_anchors / n_revisions
    solver: Optional[str]
    strategy: Optional[str]
    time_budget: Optional[Any]

def _count_revisions(meta: Dict[str, Any]) -> int:
    if not meta:
        return 0
    if "count" in meta and isinstance(meta["count"], int):
        return meta["count"]
    if "revids" in meta and isinstance(meta["revids"], list):
        return len(meta["revids"])
    if "timestamps" in meta and isinstance(meta["timestamps"], list):
        return len(meta["timestamps"])
    # fallback: partitions flatten
    parts = meta.get("partitions", [])
    if isinstance(parts, list) and parts and all(isinstance(p, list) for p in parts):
        return sum(len(p) for p in parts)
    return 0

def _chain_stats(parts: List[List[int]]) -> Tuple[float, int]:
    if not parts:
        return (0.0, 0)
    lens = [len(p) for p in parts]
    return (float(stats.mean(lens)), int(max(lens)))

def _get_title_pid(meta: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    t = meta.get("title")
    pid = meta.get("page_id")
    return t, pid


def summarize_artifact(path: str) -> ArtifactMetrics:
    article, base_texts = load(path)
    meta = getattr(article, "meta", {}) or {}
    parts = meta.get("partitions", []) or []
    anchors = getattr(article, "anchors", []) or []
    title, page_id = _get_title_pid(meta)

    # Prefer stored sizes; else try to infer (cannot recover retrospectively without storing)
    sizes = meta.get("sizes") or []

    # Revisions count
    n_revs = _count_revisions(meta)
    if not n_revs and sizes:
        n_revs = len(sizes)

    # Chain stats
    avg_chain, max_chain = _chain_stats(parts)

    # Prefer stored metrics
    space_cost = meta.get("space_cost")
    time_cost  = meta.get("time_cost")
    orig_size  = meta.get("orig_size")

    # Fallback compute if possible
    if (space_cost is None or time_cost is None) and sizes and parts:
        try:
            from ..compression.metrics import (
                space_cost_from_partitions,
                time_cost_from_partitions,
                orig_size_from_sizes,
            )
            if space_cost is None:
                space_cost = space_cost_from_partitions(sizes, parts)
            if time_cost is None:
                time_cost = time_cost_from_partitions(sizes, parts)
            if orig_size is None and sizes:
                orig_size = orig_size_from_sizes(sizes)
        except Exception:
            pass

    ratio = None
    if space_cost is not None and orig_size and orig_size > 0:
        ratio = float(space_cost) / float(orig_size)

    return ArtifactMetrics(
        artifact=os.path.abspath(path),
        title=title,
        page_id=page_id,
        n_revisions=int(n_revs or 0),
        n_anchors=len(anchors),
        n_partitions=len(parts),
        avg_chain_len=avg_chain,
        max_chain_len=max_chain,
        space_cost=space_cost if isinstance(space_cost, int) else None,
        time_cost=time_cost if isinstance(time_cost, int) else None,
        orig_size=orig_size if isinstance(orig_size, int) else None,
        compression_ratio=ratio,
        anchor_density=(len(anchors)/n_revs) if n_revs else None,
        solver=meta.get("solver"),
        strategy=meta.get("strategy"),
        time_budget=meta.get("time_budget"),
    )


def scan_artifacts(in_dir: str, pattern: str = "*.comp.gz") -> List[str]:
    return sorted(glob.glob(os.path.join(in_dir, pattern)))

def write_csv(rows: List[ArtifactMetrics], csv_path: str) -> None:
    import csv
    if not rows:
        # write empty CSV with header
        header = list(ArtifactMetrics.__annotations__.keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
        return
    header = list(asdict(rows[0]).keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

def plot_tradeoffs(rows: List[ArtifactMetrics], out_dir: str, show: bool = False) -> List[str]:
    """
    Creates:
      - space_vs_time.png  : scatter of space_cost vs time_cost
      - chain_hist.png     : histogram of chain lengths (all partitions, concatenated)
    """
    import os
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    saved = []

    # 1) Space vs Time
    xs, ys = [], []
    for r in rows:
        if r.space_cost is not None and r.time_cost is not None:
            xs.append(r.space_cost)
            ys.append(r.time_cost)
    if xs and ys:
        plt.figure()
        plt.scatter(xs, ys)             # do not set colors per project rules
        plt.xlabel("Space cost")
        plt.ylabel("Time cost")
        plt.title("Space vs Time cost")
        p1 = os.path.join(out_dir, "space_vs_time.png")
        plt.savefig(p1, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close()
        saved.append(p1)

    # 2) Chain length histogram (if we can refetch chain lengths)
    #    We only saved avg/max; try best-effort from avg/max/n_parts to synthesize, else skip.
    #    If you want exact histogram, store chain lengths list in meta during compression.
    vals = []
    for r in rows:
        # approximate by repeating avg_chain_len n_partitions times
        if r.n_partitions > 0 and r.avg_chain_len > 0:
            # don’t explode memory; cap samples
            count = min(r.n_partitions, 200)
            vals.extend([r.avg_chain_len] * count)
    if vals:
        plt.figure()
        plt.hist(vals, bins=20)          # do not set colors/styles
        plt.xlabel("Approx chain length")
        plt.ylabel("Frequency")
        plt.title("Partition chain length distribution (approx)")
        p2 = os.path.join(out_dir, "chain_hist.png")
        plt.savefig(p2, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
        plt.close()
        saved.append(p2)

    return saved

def analyze_dir(in_dir: str, out_csv: str, plots_dir: Optional[str] = None, show: bool = False) -> Dict[str, Any]:
    paths = scan_artifacts(in_dir)
    rows = [summarize_artifact(p) for p in paths]
    write_csv(rows, out_csv)

    plots = []
    if plots_dir:
        plots = plot_tradeoffs(rows, plots_dir, show=show)

    # aggregate summary
    agg = {}
    if rows:
        n = len(rows)
        crs = [r.compression_ratio for r in rows if r.compression_ratio is not None]
        agg["artifacts"] = n
        agg["avg_compression_ratio"] = float(stats.mean(crs)) if crs else None
        agg["median_compression_ratio"] = float(stats.median(crs)) if crs else None
        anchors = [r.n_anchors for r in rows if r.n_revisions]
        revs = [r.n_revisions for r in rows if r.n_revisions]
        if anchors and revs:
            ad = [a/b for a,b in zip(anchors, revs)]
            agg["avg_anchor_density"] = float(stats.mean(ad))
        tcs = [r.time_cost for r in rows if r.time_cost is not None]
        scs = [r.space_cost for r in rows if r.space_cost is not None]
        agg["avg_time_cost"] = float(stats.mean(tcs)) if tcs else None
        agg["avg_space_cost"] = float(stats.mean(scs)) if scs else None

    return {"rows": rows, "plots": plots, "aggregate": agg}
