from __future__ import annotations
import io
import os
import bz2
import xml.etree.ElementTree as ET
from typing import Iterable, Optional
from .base import Revision, RevisionSource


def _open_maybe_bz2(path: str) -> io.TextIOBase:
    """Open XML or .bz2 file transparently in text mode."""
    if path.endswith(".bz2"):
        return bz2.open(path, mode="rt", encoding="utf-8", errors="replace")
    return open(path, mode="rt", encoding="utf-8", errors="replace")


def _ns_from_tag(tag: str) -> str:
    """Extract XML namespace prefix from a tag like {namespace}mediawiki."""
    if tag.startswith("{") and "}" in tag:
        return tag.split("}")[0] + "}"
    return ""


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
