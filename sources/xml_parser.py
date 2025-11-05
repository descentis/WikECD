from __future__ import annotations
import io
import os
import bz2
import xml.etree.ElementTree as ET
from typing import Iterable, Optional, Set
from .base import Revision, RevisionSource


def _open_maybe_bz2(path: str):
    if path.endswith(".bz2"):
        return bz2.open(path, mode="rt", encoding="utf-8", errors="replace")
    return open(path, mode="rt", encoding="utf-8", errors="replace")

def _ns_and_root(context):
    # Grab root and namespace (if any)
    _, root = next(context)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    return ns, root

def _iter_pages(fh):
    """
    Yield each <page> element fully formed, then clear the root to keep memory low.
    """
    context = ET.iterparse(fh, events=("start", "end"))
    ns, root = _ns_and_root(context)
    T_PAGE = f"{ns}page"
    for event, elem in context:
        if event == "end" and elem.tag == T_PAGE:
            yield ns, elem
            # Clear accumulative tree to save memory
            root.clear()

def get_revisions_from_file(
    file_path: str,
    page_ids: Optional[Set[int]] = None,
    titles: Optional[Set[str]] = None,
    limit_per_page: Optional[int] = None,
    assume_sorted: bool = True,
    progress: bool = True,
    progress_interval: int = 250,
    max_pages_scan: Optional[int] = None,
) -> Iterable[Revision]:
    """
    Stream Revision objects for pages matching page_ids OR titles from a local dump file.
    Uses ONLY direct children for page-level fields to avoid mixing with revision fields.
    """
    # normalize selectors
    page_ids = set(page_ids) if page_ids else None
    titles = set(titles) if titles else None
    target_max_pid = max(page_ids) if page_ids else None

    scanned = 0
    with _open_maybe_bz2(file_path) as fh:
        for ns, page in _iter_pages(fh):
            scanned += 1
            if progress and progress_interval and scanned % progress_interval == 0:
                print(f"[WikECD] scanned {scanned} pages in {file_path}...")

            # ----- read page-level fields (DIRECT CHILDREN) -----
            # IMPORTANT: use './' not './/' so we don't pick up revision <id>
            title_el = page.find(f"./{ns}title")
            page_id_el = page.find(f"./{ns}id")

            title = title_el.text if title_el is not None else ""
            try:
                page_id = int(page_id_el.text) if page_id_el is not None and page_id_el.text else None
            except Exception:
                page_id = None

            # match decision
            matched = False
            if page_ids is not None and page_id is not None:
                matched = page_id in page_ids
            elif titles is not None and title:
                matched = title in titles

            if matched:
                # iterate revisions under this page
                count = 0
                for rev in page.findall(f"./{ns}revision"):
                    rid_el = rev.find(f"./{ns}id")            # revision id (child of <revision>)
                    ts_el  = rev.find(f"./{ns}timestamp")
                    txt_el = rev.find(f"./{ns}text")

                    try:
                        rid = int(rid_el.text) if rid_el is not None and rid_el.text else -1
                    except Exception:
                        rid = -1
                    ts = ts_el.text if ts_el is not None else ""
                    text = txt_el.text or "" if txt_el is not None else ""

                    yield Revision(revid=rid, timestamp=ts, text=text)
                    count += 1
                    if limit_per_page and count >= limit_per_page:
                        break

                # once found, remove from set so we can early-stop later
                if page_ids is not None and page_id in page_ids:
                    page_ids.remove(page_id)
                    if not page_ids:
                        # we got all requested ids from this file
                        return

            # Early exit if file is sorted by page_id and we've passed the target max pid
            if (assume_sorted and target_max_pid is not None
                and page_id is not None and page_id > target_max_pid):
                print(f"[WikECD] early stop: passed target pid {target_max_pid} (current {page_id})")
                return

            if max_pages_scan and scanned >= max_pages_scan:
                print(f"[WikECD] reached max_pages_scan={max_pages_scan}; stopping scan.")
                return

            # free the page element (defensive; root.clear already helps)
            page.clear()


class XMLDumpSource(RevisionSource):
    """
    Stream parser for Wikipedia XML dumps (.xml or .xml.bz2).
    Yields Revision(revid, timestamp, text) for a given title or page_id.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_revisions(
        self,
        *,
        title: Optional[str] = None,
        page_id: Optional[int] = None,
        max_revisions: Optional[int] = None,
    ) -> Iterable[Revision]:
        count = 0
        with _open_maybe_bz2(self.file_path) as fh:
            context = ET.iterparse(fh, events=("start", "end"))
            _, root = next(context)
            ns = _ns_from_tag(root.tag)
            T_PAGE = f"{ns}page"
            T_TITLE = f"{ns}title"
            T_PAGE_ID = f"{ns}id"
            T_REV = f"{ns}revision"
            T_REV_ID = f"{ns}id"
            T_TS = f"{ns}timestamp"
            T_TEXT = f"{ns}text"

            current_title = None
            current_page_id = None
            in_target_page = False

            for event, elem in context:
                if event == "end":
                    # When <title> ends, record title
                    if elem.tag == T_TITLE and current_title is None:
                        current_title = elem.text or ""

                    # When <id> ends directly inside <page> (first id), record page_id
                    elif elem.tag == T_PAGE_ID and current_page_id is None:
                        try:
                            current_page_id = int(elem.text)
                        except Exception:
                            current_page_id = None

                        # Now decide if this page matches
                        match_title = (title is None) or (current_title == title)
                        match_id = (page_id is None) or (current_page_id == page_id)
                        in_target_page = match_title and match_id

                    # Handle <revision> blocks only inside matching page
                    elif elem.tag == T_REV and in_target_page:
                        rid_el = elem.find(T_REV_ID)
                        ts_el = elem.find(T_TS)
                        txt_el = elem.find(f".//{T_TEXT}")

                        try:
                            rid = int(rid_el.text) if rid_el is not None and rid_el.text else -1
                        except Exception:
                            rid = -1
                        ts = ts_el.text if ts_el is not None else ""
                        text = txt_el.text or "" if txt_el is not None else ""

                        yield Revision(revid=rid, timestamp=ts, text=text)
                        count += 1
                        if max_revisions and count >= max_revisions:
                            return

                        elem.clear()

                    # When </page> ends, reset state
                    elif elem.tag == T_PAGE:
                        current_title = None
                        current_page_id = None
                        in_target_page = False
                        elem.clear()
                        root.clear()
