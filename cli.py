from __future__ import annotations
import argparse, sys
from typing import Dict
from .sources.api_client import MediaWikiAPISource
from .sources.xml_parser import XMLDumpSource
from .compression.compressor import compress_article
from .storage.serializer import save, load
from .retrieval.retrieval import retrieve_range
from .retrieval.query import retrieve_by_revid, retrieve_by_time

from .sources.dump_locator import list_meta_history_parts, pick_parts_for_pageids, ensure_download
from .sources.api_client import resolve_page_ids


def main():
    ap = argparse.ArgumentParser(prog="wikecd", description="Wikipedia Efficient Compression & Decompression")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # compress from API
    ap_api = sub.add_parser("compress-api", help="Compress from Wikipedia API")
    ap_api.add_argument("--title", required=True)
    ap_api.add_argument("--limit", type=int, default=50)
    ap_api.add_argument("--out", required=True)
    ap_api.add_argument("--time-budget", type=int, default=None)
    ap_api.add_argument("--user-agent", default=None, help="Custom User-Agent with contact info")
    ap_api.add_argument("--verbose", action="store_true")

    # add arguments
    ap_api.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_api.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_api.add_argument("--eps", type=float, default=0.1, help="FPTAS epsilon (smaller = better, slower)")
    ap_api.add_argument("--max-states", type=int, default=100000, help="Sparse DP state cap")

    # subparser
    ap_fromdump = sub.add_parser("compress-from-dump", help="Compress selected pages from a Wikimedia dump date")
    ap_fromdump.add_argument("--dump", required=True,
                             help="Dump root URL, e.g. https://dumps.wikimedia.org/enwiki/20251001/")
    ap_fromdump.add_argument("--titles", default=None,
                             help='Comma-separated titles, e.g. "Python (programming language),Ada Lovelace"')
    ap_fromdump.add_argument("--page-ids", default=None, help="Comma-separated numeric page IDs")
    ap_fromdump.add_argument("--out-dir", required=True, help="Directory to store .comp.gz per article")
    ap_fromdump.add_argument("--download-dir", default="downloads", help="Where to cache history .bz2 files")
    ap_fromdump.add_argument("--user-agent", default=None)
    ap_fromdump.add_argument("--verbose", action="store_true")
    # compression tuning (reuse existing flags)
    ap_fromdump.add_argument("--time-budget", type=int, default=None)
    ap_fromdump.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_fromdump.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_fromdump.add_argument("--eps", type=float, default=0.1)
    ap_fromdump.add_argument("--max-states", type=int, default=100000)
    ap_fromdump.add_argument("--limit-revs", type=int, default=None, help="Optional cap for testing")

    # compress from XML
    ap_xml = sub.add_parser("compress-xml", help="Compress from XML dump")
    ap_xml.add_argument("--xml", required=True)
    ap_xml.add_argument("--title", help="Filter by title (optional)")
    ap_xml.add_argument("--count", type=int, default=200, help="Max revisions to process (first N)")
    ap_xml.add_argument("--out", required=True)
    ap_xml.add_argument("--time-budget", type=int, default=None)

    ap_xml.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_xml.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_xml.add_argument("--eps", type=float, default=0.1)
    ap_xml.add_argument("--max-states", type=int, default=100000)

    # retrieve by revision ID
    ap_byid = sub.add_parser("retrieve-by-id", help="Retrieve by Wikipedia revision IDs")
    ap_byid.add_argument("--in", dest="inp", required=True)
    ap_byid.add_argument("--ids", required=True, help="Comma-separated list of revision IDs")
    ap_byid.add_argument("--print", action="store_true")

    # retrieve by timestamp range
    ap_bytime = sub.add_parser("retrieve-by-time", help="Retrieve by timestamp range (ISO)")
    ap_bytime.add_argument("--in", dest="inp", required=True)
    ap_bytime.add_argument("--start-ts", default=None, help='Start ts e.g. "2021-01-01" or "2021-01-01T00:00:00Z"')
    ap_bytime.add_argument("--end-ts", default=None, help='End ts e.g. "2021-01-31" or "2021-01-31T23:59:59Z"')
    ap_bytime.add_argument("--print", action="store_true")

    # retrieve
    ap_get = sub.add_parser("retrieve", help="Retrieve revisions from a compressed file")
    ap_get.add_argument("--in", dest="inp", required=True)
    ap_get.add_argument("--start", type=int, required=True)
    ap_get.add_argument("--length", type=int, default=0)
    ap_get.add_argument("--print", action="store_true", help="Print the last retrieved revision")

    ap_dbg = sub.add_parser("debug-resolve", help="Resolve titles to page IDs and show chosen dump parts")
    ap_dbg.add_argument("--dump", required=True)
    ap_dbg.add_argument("--titles", required=True)
    ap_dbg.add_argument("--user-agent", default=None)

    # history
    ap_hist = sub.add_parser("compress-from-history-file",
                             help="Compress one or more pages from a specific pages-meta-history file (.bz2 or .7z)")
    ap_hist.add_argument("--file", required=True, help="HTTP(S) URL or local path to pages-meta-history*.xml.bz2/.7z")
    ap_hist.add_argument("--page-ids", required=True, help="Comma-separated numeric page IDs to extract")
    ap_hist.add_argument("--out-dir", required=True)
    ap_hist.add_argument("--download-dir", default="downloads")
    ap_hist.add_argument("--user-agent", default=None)
    ap_hist.add_argument("--limit-revs", type=int, default=None)

    # compression knobs
    ap_hist.add_argument("--time-budget", type=int, default=None)
    ap_hist.add_argument("--solver", choices=["heuristic", "exact"], default="heuristic")
    ap_hist.add_argument("--strategy", choices=["auto", "greedy", "fptas", "sparse"], default="auto")
    ap_hist.add_argument("--eps", type=float, default=0.1)
    ap_hist.add_argument("--max-states", type=int, default=100000)
    ap_hist.add_argument("--verbose", action="store_true")

    args = ap.parse_args()

    if args.cmd == "compress-api":
        src = MediaWikiAPISource(user_agent=args.user_agent, verbose=args.verbose)
        revs = list(src.get_revisions(title=args.title, limit=args.limit))
        article = compress_article(
            args.title, revs, time_budget=args.time_budget,
            solver=args.solver, strategy=args.strategy, eps=args.eps, max_states=args.max_states
        )
        # build base_texts for anchors
        texts = [r.text for r in revs]
        base_texts: Dict[int, str] = {base: texts[base] for base in article.anchors}
        save(args.out, article, base_texts)
        print(f"[OK] Compressed {len(revs)} revisions -> {args.out}")


    elif args.cmd == "compress-xml":

        src = XMLDumpSource(args.xml)

        # STREAM revisions directly with a built-in cap

        revs_iter = src.get_revisions(title=args.title, max_revisions=args.count)

        revs = list(revs_iter)  # For a single page this is OK; count keeps it bounded.

        article = compress_article(

            args.title or "XML-Article",

            revs,

            time_budget=args.time_budget,

            solver=args.solver,

            strategy=args.strategy,

            eps=args.eps,

            max_states=args.max_states,

        )

        texts = [r.text for r in revs]

        base_texts = {base: texts[base] for base in article.anchors}

        save(args.out, article, base_texts)

        print(f"[OK] Compressed {len(revs)} revisions -> {args.out}")

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


    elif args.cmd == "compress-from-dump":
        import os, json, csv, time
        from .sources.dump_locator import list_meta_history_parts, pick_parts_for_pageids, ensure_download
        from .sources.api_client import resolve_page_ids
        from .sources.xml_parser import XMLDumpSource
        from .compression.compressor import compress_article
        from .storage.serializer import save
        try:
            from tqdm import tqdm
        except Exception:
            tqdm = None
        # 1) Resolve page IDs (titles and/or explicit page-ids)
        page_ids: Dict[str, int] = {}
        if args.titles:
            titles = [t.strip() for t in args.titles.split(",") if t.strip()]
            page_ids.update(resolve_page_ids(titles, user_agent=args.user_agent))
        if args.page_ids:
            for pid in args.page_ids.split(","):
                pid = pid.strip()
                if pid.isdigit():
                    page_ids[pid] = int(pid)
        if not page_ids:
            raise SystemExit("No titles or page IDs provided.")
        print(f"[WikECD] Need {len(page_ids)} pages")
        # 2) List dump parts and map page_ids -> part
        parts = list_meta_history_parts(args.dump, user_agent=args.user_agent, verbose=args.verbose)
        pid_to_part = pick_parts_for_pageids(parts, page_ids.values())
        missing = [pid for pid in page_ids.values() if pid not in pid_to_part]
        if missing:
            print("[WikECD] WARNING: Some page_ids not found in dump ranges:", missing)
        part_to_pids: Dict[str, List[int]] = {}
        for title_or_pid, pid in page_ids.items():
            part = pid_to_part.get(pid)
            if not part:
                continue
            part_to_pids.setdefault(part.fname, []).append(pid)
        print(f"[WikECD] Will fetch {len(part_to_pids)} dump file(s) covering requested pages")
        os.makedirs(args.out_dir, exist_ok=True)
        # Manifest entries we’ll accumulate
        manifest_rows = []
        start_all = time.time()
        for part_fname, pids in part_to_pids.items():
            part = next(p for p in parts if p.fname == part_fname)
            local_path = ensure_download(part.url, args.download_dir, user_agent=args.user_agent)
            print(f"[WikECD] Parsing {part.fname} for {len(pids)} page(s)")
            src = XMLDumpSource(local_path)
            for pid in pids:
                # Prepare parsing progress bar (unknown total unless --limit-revs provided)
                bar = None
                revs = []
                parsed = 0
                total_hint = args.limit_revs if args.limit_revs else None
                title = next((k for k, v in page_ids.items() if v == pid), f"page_{pid}")
                if tqdm:
                    bar = tqdm(total=total_hint, unit="rev", desc=f"Parsing {title} (pid {pid})")
                # STREAM revisions and collect to list (needed for compression)
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
                # Append to manifest
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
        # Write manifest (JSON + CSV)
        manifest_json = os.path.join(args.out_dir, "manifest.json")
        manifest_csv = os.path.join(args.out_dir, "manifest.csv")
        with open(manifest_json, "w", encoding="utf-8") as f:
            json.dump({
                "dump": args.dump,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "count": len(manifest_rows),
                "items": manifest_rows
            }, f, ensure_ascii=False, indent=2)
        # CSV
        if manifest_rows:
            fieldnames = list(manifest_rows[0].keys())
            with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(manifest_rows)
        print(f"[WikECD] Manifest written: {manifest_json}")
        print(f"[WikECD] Manifest written: {manifest_csv}")

    elif args.cmd == "debug-resolve":
        from WikECD.sources.api_client import resolve_page_ids
        from WikECD.sources.dump_locator import list_meta_history_parts, pick_parts_for_pageids
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]
        ids = resolve_page_ids(titles, user_agent=args.user_agent)
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

        target = args.file
        # If it's a URL, download to cache first
        parsed = urlparse(target)
        if parsed.scheme in ("http", "https"):
            local_path = ensure_download(target, args.download_dir, user_agent=args.user_agent)
        else:
            local_path = target

        os.makedirs(args.out_dir, exist_ok=True)

        pids = [int(x.strip()) for x in args.page_ids.split(",") if x.strip().isdigit()]
        src = XMLDumpSource(local_path)

        for pid in pids:
            if args.verbose:
                print(f"[WikECD] Streaming page_id={pid} from {local_path}")
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


if __name__ == "__main__":
    main()
