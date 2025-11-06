from __future__ import annotations
import argparse
import sys
import os
from typing import Dict, List, Optional

# core modules
from .sources.api_client import MediaWikiAPISource, resolve_page_ids
from .sources.xml_parser import XMLDumpSource
from .compression.compressor import compress_article
from .storage.serializer import save, load
from .retrieval.retrieval import retrieve_range
from .retrieval.query import retrieve_by_revid, retrieve_by_time

# helpers for dumps
from .cli_helpers.dump_sweeper import extract_from_dump_dir
from .sources.dump_locator import list_meta_history_parts, pick_parts_for_pageids, ensure_download

# logger helper (optional)
from .logger import get_logger

logger = get_logger("WikECD.cli")

DEFAULT_USER_AGENT = "WikECD/0.1 (+contact: you@example.com)"


def _ensure_user_agent(ua: Optional[str]) -> str:
    return ua if ua else DEFAULT_USER_AGENT


def main():
    ap = argparse.ArgumentParser(prog="wikecd", description="Wikipedia Efficient Compression & Decompression")
    subparsers = ap.add_subparsers(dest="cmd", required=True)

    # compress from API
    ap_api = subparsers.add_parser("compress-api", help="Compress from Wikipedia API")
    ap_api.add_argument("--title", required=True)
    ap_api.add_argument("--limit", type=int, default=50)
    ap_api.add_argument("--out", required=True)
    ap_api.add_argument("--time-budget", type=int, default=None)
    ap_api.add_argument("--user-agent", default=None, help="Custom User-Agent with contact info")
    ap_api.add_argument("--verbose", action="store_true")
    ap_api.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_api.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_api.add_argument("--eps", type=float, default=0.1, help="FPTAS epsilon (smaller = better, slower)")
    ap_api.add_argument("--max-states", type=int, default=100000, help="Sparse DP state cap")

    # compress-from-dump (remote dump locator + download)
    ap_fromdump = subparsers.add_parser("compress-from-dump", help="Compress selected pages from a Wikimedia dump date")
    ap_fromdump.add_argument("--dump", required=True,
                             help="Dump root URL, e.g. https://dumps.wikimedia.org/enwiki/20251001/")
    ap_fromdump.add_argument("--titles", default=None,
                             help='Comma-separated titles, e.g. "Python (programming language),Ada Lovelace"')
    ap_fromdump.add_argument("--page-ids", default=None, help="Comma-separated numeric page IDs")
    ap_fromdump.add_argument("--out-dir", required=True, help="Directory to store .comp.gz per article")
    ap_fromdump.add_argument("--download-dir", default="downloads", help="Where to cache history .bz2 files")
    ap_fromdump.add_argument("--user-agent", default=None)
    ap_fromdump.add_argument("--verbose", action="store_true")
    ap_fromdump.add_argument("--time-budget", type=int, default=None)
    ap_fromdump.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_fromdump.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_fromdump.add_argument("--eps", type=float, default=0.1)
    ap_fromdump.add_argument("--max-states", type=int, default=100000)
    ap_fromdump.add_argument("--limit-revs", type=int, default=None, help="Optional cap for testing")

    # compress-from-dump-dir (local dump directory index + sweep)
    # ---------------------------------------------------------------------
    ap_fromdumpdir = subparsers.add_parser("compress-from-dump-dir", help="Compress pages from a local dump directory")
    ap_fromdumpdir.add_argument("--dump-dir", required=True, help="Local directory containing .bz2 history files")
    ap_fromdumpdir.add_argument("--page-ids", required=True, help="Comma-separated page ids")
    ap_fromdumpdir.add_argument("--out-dir", required=True, help="Output directory for compressed artifacts")
    ap_fromdumpdir.add_argument("--index", required=False, help="Optional path to write/read dump index JSON")
    ap_fromdumpdir.add_argument("--solver", default="heuristic", choices=["heuristic", "exact"])
    ap_fromdumpdir.add_argument("--strategy", default="fptas", choices=["auto", "greedy", "fptas", "sparse"])
    ap_fromdumpdir.add_argument("--eps", type=float, default=0.1)
    ap_fromdumpdir.add_argument("--max-pages-scan", type=int, default=None, help="Optional limit for XML scan pages")

    # 🚀 NEW PERFORMANCE FLAGS
    ap_fromdumpdir.add_argument("--jobs", type=int, default=1, help="Parallel worker count (default: 1)")
    ap_fromdumpdir.add_argument("--resume", action="store_true", help="Skip already-compressed pages if present")
    ap_fromdumpdir.add_argument("--force", action="store_true", help="Force recompress even if output exists")
    ap_fromdumpdir.add_argument("--auto-index", action="store_true", help="Auto-build .pageidx.sqlite for faster seeks")
    ap_fromdumpdir.add_argument("--verbose", action="store_true", help="Verbose logging")

    # compress-xml (single local XML file)
    ap_xml = subparsers.add_parser("compress-xml", help="Compress from XML dump")
    ap_xml.add_argument("--xml", required=True)
    ap_xml.add_argument("--title", help="Filter by title (optional)")
    ap_xml.add_argument("--count", type=int, default=200, help="Max revisions to process (first N)")
    ap_xml.add_argument("--out", required=True)
    ap_xml.add_argument("--time-budget", type=int, default=None)
    ap_xml.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_xml.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_xml.add_argument("--eps", type=float, default=0.1)
    ap_xml.add_argument("--max-states", type=int, default=100000)

    # retrieve-by-id
    ap_byid = subparsers.add_parser("retrieve-by-id", help="Retrieve by Wikipedia revision IDs")
    ap_byid.add_argument("--in", dest="inp", required=True)
    ap_byid.add_argument("--ids", required=True, help="Comma-separated list of revision IDs")
    ap_byid.add_argument("--print", action="store_true")

    # retrieve-by-time
    ap_bytime = subparsers.add_parser("retrieve-by-time", help="Retrieve by timestamp range (ISO)")
    ap_bytime.add_argument("--in", dest="inp", required=True)
    ap_bytime.add_argument("--start-ts", default=None, help='Start ts e.g. "2021-01-01" or "2021-01-01T00:00:00Z"')
    ap_bytime.add_argument("--end-ts", default=None, help='End ts e.g. "2021-01-31" or "2021-01-31T23:59:59Z"')
    ap_bytime.add_argument("--print", action="store_true")

    # retrieve
    ap_get = subparsers.add_parser("retrieve", help="Retrieve revisions from a compressed file")
    ap_get.add_argument("--in", dest="inp", required=True)
    ap_get.add_argument("--start", type=int, required=True)
    ap_get.add_argument("--length", type=int, default=0)
    ap_get.add_argument("--print", action="store_true", help="Print the last retrieved revision")

    # debug-resolve
    ap_dbg = subparsers.add_parser("debug-resolve", help="Resolve titles to page IDs and show chosen dump parts")
    ap_dbg.add_argument("--dump", required=True)
    ap_dbg.add_argument("--titles", required=True)
    ap_dbg.add_argument("--user-agent", default=None)

    # compress-from-history-file
    ap_hist = subparsers.add_parser("compress-from-history-file",
                             help="Compress one or more pages from a specific pages-meta-history file (.bz2 or .7z)")
    ap_hist.add_argument("--file", required=True, help="HTTP(S) URL or local path to pages-meta-history*.xml.bz2/.7z")
    ap_hist.add_argument("--page-ids", required=True, help="Comma-separated numeric page IDs to extract")
    ap_hist.add_argument("--out-dir", required=True)
    ap_hist.add_argument("--download-dir", default="downloads")
    ap_hist.add_argument("--user-agent", default=None)
    ap_hist.add_argument("--limit-revs", type=int, default=None)
    ap_hist.add_argument("--time-budget", type=int, default=None)
    ap_hist.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_hist.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_hist.add_argument("--eps", type=float, default=0.1)
    ap_hist.add_argument("--max-states", type=int, default=100000)
    ap_hist.add_argument("--verbose", action="store_true")

    # build-bz2-index
    ap_bz2idx = subparsers.add_parser("build-bz2-index", help="Build per-file page index for a bz2 history file")
    ap_bz2idx.add_argument("--file", required=True, help="pages-meta-history*.xml.bz2")
    ap_bz2idx.add_argument("--index", required=True, help="SQLite path to write index (e.g., file.pageidx.sqlite)")

    # compress-from-history-file (add flag)
    ap_hist.add_argument("--use-index", default=None, help="Optional SQLite index path built by build-bz2-index")

    # analyze-comp
    ap_an = subparsers.add_parser("analyze-comp", help="Analyze compressed artifacts and plot trade-offs")
    ap_an.add_argument("--in-dir", required=True, help="Directory containing .comp.gz artifacts")
    ap_an.add_argument("--out-csv", required=True, help="Path to write CSV summary")
    ap_an.add_argument("--plots-dir", default=None, help="Directory to save PNG charts (optional)")
    ap_an.add_argument("--show", action="store_true", help="Show plots interactively")

    args = ap.parse_args()

    # dispatch
    if args.cmd == "compress-api":
        from .compression.compressor import compress_article
        from .storage.serializer import save
        ua = _ensure_user_agent(args.user_agent)
        src = MediaWikiAPISource(user_agent=ua, verbose=args.verbose)
        revs = list(src.get_revisions(title=args.title, limit=args.limit))
        article = compress_article(
            args.title, revs, time_budget=args.time_budget,
            solver=args.solver, strategy=args.strategy, eps=args.eps, max_states=args.max_states
        )
        texts = [r.text for r in revs]
        base_texts: Dict[int, str] = {base: texts[base] for base in article.anchors}
        save(args.out, article, base_texts)
        print(f"[OK] Compressed {len(revs)} revisions -> {args.out}")

    elif args.cmd == "compress-xml":
        src = XMLDumpSource(args.xml)
        revs_iter = src.get_revisions(title=args.title, max_revisions=args.count)
        revs = list(revs_iter)
        if not revs:
            print("[WikECD] No revisions found in XML for given title/filters.")
            raise SystemExit(1)
        article = compress_article(
            args.title or "XML-Article", revs, time_budget=args.time_budget,
            solver=args.solver, strategy=args.strategy, eps=args.eps, max_states=args.max_states,
        )
        texts = [r.text for r in revs]
        base_texts = {base: texts[base] for base in article.anchors}
        save(args.out, article, base_texts)
        print(f"[OK] Compressed {len(revs)} revisions -> {args.out}")

    elif args.cmd == "compress-from-dump":
        ua = _ensure_user_agent(args.user_agent)
        page_ids_map: Dict[str, int] = {}
        if args.titles:
            titles = [t.strip() for t in args.titles.split(",") if t.strip()]
            page_ids_map.update(resolve_page_ids(titles, user_agent=ua))
        if args.page_ids:
            for pid in args.page_ids.split(","):
                pid = pid.strip()
                if pid.isdigit():
                    page_ids_map[pid] = int(pid)
        if not page_ids_map:
            raise SystemExit("No titles or page IDs provided.")
        print(f"[WikECD] Need {len(page_ids_map)} pages")
        parts = list_meta_history_parts(args.dump, user_agent=ua, verbose=args.verbose)
        pid_to_part = pick_parts_for_pageids(parts, page_ids_map.values())
        missing = [pid for pid in page_ids_map.values() if pid not in pid_to_part]
        if missing:
            print("[WikECD] WARNING: Some page_ids not found in dump ranges:", missing)
        part_to_pids: Dict[str, List[int]] = {}
        for title_or_pid, pid in page_ids_map.items():
            part = pid_to_part.get(pid)
            if not part:
                continue
            part_to_pids.setdefault(part.fname, []).append(pid)
        print(f"[WikECD] Will fetch {len(part_to_pids)} dump file(s) covering requested pages")
        os.makedirs(args.out_dir, exist_ok=True)
        import time, json, csv
        manifest_rows = []
        for part_fname, pids in part_to_pids.items():
            part = next(p for p in parts if p.fname == part_fname)
            local_path = ensure_download(part.url, args.download_dir, user_agent=ua)
            print(f"[WikECD] Parsing {part.fname} for {len(pids)} page(s)")
            src = XMLDumpSource(local_path)
            try:
                from tqdm import tqdm
            except Exception:
                tqdm = None
            for pid in pids:
                bar = None
                revs = []
                parsed = 0
                total_hint = args.limit_revs if args.limit_revs else None
                title = next((k for k, v in page_ids_map.items() if v == pid), f"page_{pid}")
                if tqdm:
                    bar = tqdm(total=total_hint, unit="rev", desc=f"Parsing {title} (pid {pid})")
                for r in src.get_revisions(page_id=pid, max_revisions=args.limit_revs):
                    revs.append(r)
                    parsed += 1
                    if bar:
                        bar.update(1)
                if bar:
                    bar.close()
                if not revs:
                    print(f"[WikECD] No revisions found for page_id {pid} in {part.fname}")
                    continue
                print(f"[WikECD] Compressing {title} ({len(revs)} revs)")
                t0 = time.time()
                article = compress_article(
                    title, revs, time_budget=args.time_budget,
                    solver=args.solver, strategy=args.strategy, eps=args.eps, max_states=args.max_states
                )
                texts = [r.text for r in revs]
                base_texts = {b: texts[b] for b in article.anchors}
                out_path = os.path.join(args.out_dir, f"{title}.comp.gz")
                save(out_path, article, base_texts)
                t1 = time.time()
                manifest_rows.append({
                    "title": title,
                    "page_id": pid,
                    "dump_file": part.fname,
                    "dump_url": part.url,
                    "revisions": len(revs),
                    "anchors": len(article.anchors),
                    "partitions": len(article.meta.get("partitions", [])),
                    "time_budget": args.time_budget if args.time_budget is not None else f"{len(revs)}^2",
                    "solver": args.solver,
                    "strategy": args.strategy,
                    "eps": args.eps if args.solver == "heuristic" and args.strategy == "fptas" else None,
                    "max_states": args.max_states if args.solver == "heuristic" and args.strategy == "sparse" else None,
                    "artifact": out_path,
                    "compress_seconds": round(t1 - t0, 3),
                })
                print(f"[OK] {title} -> {out_path}")
        manifest_json = os.path.join(args.out_dir, "manifest.json")
        manifest_csv = os.path.join(args.out_dir, "manifest.csv")
        with open(manifest_json, "w", encoding="utf-8") as f:
            json.dump({
                "dump": args.dump,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "count": len(manifest_rows),
                "items": manifest_rows
            }, f, ensure_ascii=False, indent=2)
        if manifest_rows:
            fieldnames = list(manifest_rows[0].keys())
            with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(manifest_rows)
        print(f"[WikECD] Manifest written: {manifest_json}")
        print(f"[WikECD] Manifest written: {manifest_csv}")

    elif args.cmd == "compress-from-dump-dir":
        from .cli_helpers.dump_sweeper import extract_from_dump_dir
        page_ids = [int(x.strip()) for x in args.page_ids.split(",") if x.strip().isdigit()]
        if not page_ids:
            raise SystemExit("No valid numeric page IDs provided.")
        extract_from_dump_dir(
            dump_dir=args.dump_dir,
            page_ids=page_ids,
            out_dir=args.out_dir,
            index_path=args.index,
            solver=args.solver,
            strategy=args.strategy,
            eps=args.eps,
            max_pages_scan=args.max_pages_scan,
            verbose=args.verbose,
            jobs=args.jobs,
            resume=args.resume,
            force=args.force,
            auto_index=args.auto_index,
        )

        print(f"[WikECD] Completed dump-dir compression for {len(page_ids)} page(s).")

    elif args.cmd == "debug-resolve":
        ua = _ensure_user_agent(args.user_agent)
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]
        ids = resolve_page_ids(titles, user_agent=ua)
        print("[WikECD] Resolved IDs:", ids)
        parts = list_meta_history_parts(args.dump)
        pid_to_part = pick_parts_for_pageids(parts, ids.values())
        for t, pid in ids.items():
            part = pid_to_part.get(pid)
            if part:
                print(f"{t}: pid={pid} -> {part.fname} [{part.start}-{part.end}]")
            else:
                print(f"{t}: pid={pid} -> NO MATCHING HISTORY PART")

    elif args.cmd == "compress-from-history-file":
        from urllib.parse import urlparse
        from WikECD.sources.dump_locator import ensure_download
        from WikECD.sources.xml_parser import XMLDumpSource
        from WikECD.compression.compressor import compress_article
        from WikECD.storage.serializer import save
        import os

        target = args.file
        parsed = urlparse(target)
        if parsed.scheme in ("http", "https"):
            local_path = ensure_download(target, args.download_dir, user_agent=_ensure_user_agent(args.user_agent))
        else:
            local_path = target

        os.makedirs(args.out_dir, exist_ok=True)

        pids = [int(x.strip()) for x in args.page_ids.split(",") if x.strip().isdigit()]
        src = XMLDumpSource(local_path)

        use_index = args.use_index  # might be None

        for pid in pids:
            if args.verbose:
                print(f"[WikECD] Streaming page_id={pid} from {local_path}" if not use_index
                      else f"[WikECD] Seeking page_id={pid} via index {use_index}")

            if use_index:
                # FAST SEEK PATH
                from WikECD.sources.fast_page_reader import iter_revisions_fast
                revs = list(iter_revisions_fast(local_path, use_index, pid))
            else:
                # STREAMING FALLBACK
                revs = list(src.get_revisions(page_id=pid, max_revisions=args.limit_revs))

            if not revs:
                print(f"[WikECD] No revisions found for page_id {pid} in {local_path}")
                continue

            # Title is unknown here; use page_id as name (or set later if you have a map)
            title = f"page_{pid}"
            article = compress_article(
                title, revs, time_budget=args.time_budget,
                solver=args.solver, strategy=args.strategy, eps=args.eps, max_states=args.max_states
            )
            texts = [r.text for r in revs]
            base_texts = {b: texts[b] for b in article.anchors}
            out_path = os.path.join(args.out_dir, f"{title}.comp.gz")
            save(out_path, article, base_texts)
            print(f"[OK] {title} -> {out_path}")

    elif args.cmd == "retrieve":
        article, base_texts = load(args.inp)
        outs = retrieve_range(article, base_texts, start=args.start, length=args.length)
        print(f"[OK] Retrieved {len(outs)} revisions (indices {args.start}..{args.start+args.length})")
        if args.print and outs:
            print("--- LAST REVISION ---")
            sys.stdout.write(outs[-1])

    elif args.cmd == "retrieve-by-id":
        article, base_texts = load(args.inp)
        ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        outs = retrieve_by_revid(article, base_texts, ids)
        print(f"[OK] Retrieved {len(outs)} revisions for {len(ids)} requested IDs.")
        if args.print and outs:
            print("--- LAST REVISION ---")
            sys.stdout.write(outs[-1])

    elif args.cmd == "retrieve-by-time":
        article, base_texts = load(args.inp)
        outs = retrieve_by_time(article, base_texts, start=args.start_ts, end=args.end_ts)
        print(f"[OK] Retrieved {len(outs)} revisions in range [{args.start_ts} .. {args.end_ts}].")
        if args.print and outs:
            print("--- LAST REVISION ---")
            sys.stdout.write(outs[-1])

    elif args.cmd == "build-bz2-index":
        from WikECD.sources.bz2_page_index import build_page_index
        n = build_page_index(args.file, args.index)
        print(f"[OK] Indexed {n} pages -> {args.index}")

    elif args.cmd == "analyze-comp":
        from WikECD.analytics.analyze import analyze_dir
        res = analyze_dir(args.in_dir, args.out_csv, plots_dir=args.plots_dir, show=args.show)
        print(f"[WikECD] Wrote CSV: {args.out_csv}")
        if args.plots_dir:
            for p in res["plots"]:
                print(f"[WikECD] Plot: {p}")
        agg = res.get("aggregate", {})
        if agg:
            print("[WikECD] Summary:",
                  f"artifacts={agg.get('artifacts')},",
                  f"avg_ratio={agg.get('avg_compression_ratio')},",
                  f"median_ratio={agg.get('median_compression_ratio')},",
                  f"avg_anchor_density={agg.get('avg_anchor_density')},",
                  f"avg_time_cost={agg.get('avg_time_cost')},",
                  f"avg_space_cost={agg.get('avg_space_cost')}")


    else:
        ap.print_help()


if __name__ == "__main__":
    main()
