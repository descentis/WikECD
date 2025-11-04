import os
from pathlib import Path
import pytest

from WikECD.sources.xml_parser import XMLDumpSource
from WikECD.sources.api_client import resolve_page_ids

DATA_DIR = Path(__file__).parent / "data"


def test_xml_parser_reads_revisions(tmp_path):
    fp = DATA_DIR / "sample_history.xml"
    src = XMLDumpSource(str(fp))
    revs = list(src.get_revisions(title="WikECD Demo"))
    assert len(revs) == 2
    assert revs[0].revid == 1
    assert "hello" in revs[0].text

    revs_by_id = list(src.get_revisions(page_id=2000))
    assert len(revs_by_id) == 1
    assert revs_by_id[0].revid == 10


def test_resolve_page_ids_live(monkeypatch):
    # This test calls the real API only if network allowed.
    # If requests are not desired in CI, mark it xfail via env var.
    import os
    if os.environ.get("WIKECD_NO_NETWORK") == "1":
        pytest.skip("Network disabled for tests")
    ids = resolve_page_ids(["Python (programming language)"], user_agent="WikECD-test/0.1")
    assert isinstance(ids, dict)
    # if API reachable, it should resolve to a pageid int
    if ids:
        v = list(ids.values())[0]
        assert isinstance(v, int)
