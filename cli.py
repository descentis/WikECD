from __future__ import annotations
import argparse, sys
from typing import Dict
from .sources.api_client import MediaWikiAPISource
from .sources.xml_parser import XMLDumpSource
from .compression.compressor import compress_article
from .storage.serializer import save, load
from .retrieval.retrieval import retrieve_range
from .retrieval.query import retrieve_by_revid, retrieve_by_time


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

    # compress from XML
    ap_xml = sub.add_parser("compress-xml", help="Compress from XML dump")
    ap_xml.add_argument("--xml", required=True)
    ap_xml.add_argument("--title", help="Filter by title (optional)")
    ap_xml.add_argument("--count", type=int, default=200, help="Max revisions to process (first N)")
    ap_xml.add_argument("--out", required=True)
    ap_xml.add_argument("--time-budget", type=int, default=None)

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

    args = ap.parse_args()

    if args.cmd == "compress-api":
        src = MediaWikiAPISource(user_agent=args.user_agent, verbose=args.verbose)
        revs = list(src.get_revisions(title=args.title, limit=args.limit))
        article = compress_article(args.title, revs, time_budget=args.time_budget)
        # build base_texts for anchors
        texts = [r.text for r in revs]
        base_texts: Dict[int, str] = {base: texts[base] for base in article.anchors}
        save(args.out, article, base_texts)
        print(f"[OK] Compressed {len(revs)} revisions -> {args.out}")

    elif args.cmd == "compress-xml":
        src = XMLDumpSource(args.xml)
        # stream then cut to count (keeps memory sane)
        revs_iter = src.get_revisions(title=args.title)
        revs = []
        for i, r in enumerate(revs_iter):
            revs.append(r)
            if i + 1 >= args.count:
                break
        article = compress_article(args.title or "XML-Article", revs, time_budget=args.time_budget)
        texts = [r.text for r in revs]
        base_texts: Dict[int, str] = {base: texts[base] for base in article.anchors}
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


if __name__ == "__main__":
    main()
