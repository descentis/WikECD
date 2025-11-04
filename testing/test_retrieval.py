from pathlib import Path
import pytest
from WikECD.compression.compressor import compress_article
from WikECD.retrieval.retrieval import reconstruct_range
from WikECD.sources.xml_parser import XMLDumpSource


def test_roundtrip_compress_retrieve():
    # create small revisions in memory
    # create fake Revision objects to feed compress_article
    from WikECD.sources.base import Revision
    revs = [
        Revision(revid=1, timestamp="2024-01-01T00:00Z", text="a"),
        Revision(revid=2, timestamp="2024-01-02T00:00Z", text="ab"),
        Revision(revid=3, timestamp="2024-01-03T00:00Z", text="abc"),
    ]
    article = compress_article("test-page", revs, time_budget=9, solver="heuristic", strategy="greedy")
    # reconstruct revision 2..3
    texts = reconstruct_range(article, 1, 2)  # depending on your API signature
    assert isinstance(texts, list)
    # last revision text should match original
    assert texts[-1] == revs[2].text
