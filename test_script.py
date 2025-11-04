from WikECD.sources.base import Revision
from WikECD.compression.compressor import compress_article
from WikECD.retrieval.retrieval import reconstruct_range

revs = [
    Revision(revid=1, timestamp="2024-01-01T00:00Z", text="a"),
    Revision(revid=2, timestamp="2024-01-02T00:00Z", text="ab"),
    Revision(revid=3, timestamp="2024-01-03T00:00Z", text="abc"),
]

article = compress_article("test-page", revs, time_budget=9, solver="heuristic", strategy="greedy")
print("anchors:", getattr(article, "anchors", None))
print("base_texts:", getattr(article, "base_texts", None))
texts = reconstruct_range(article, 1, 2)
print("reconstructed:", texts)
