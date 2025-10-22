from WikECD.sources.api_client import MediaWikiAPISource
from WikECD.compression.compressor import compress_article
from WikECD.retrieval.retrieval import retrieve_range

if __name__ == "__main__":
    src = MediaWikiAPISource()
    title = "Python (programming language)"
    revs = list(src.get_revisions(title=title, limit=50))
    article = compress_article(title, revs, time_budget=None)  # defaults to n^2

    # build base texts map for anchors
    base_texts = {}
    texts = [r.text for r in revs]
    for base_idx in article.anchors:
        base_texts[base_idx] = texts[base_idx]

    # get revisions 10..15
    out = retrieve_range(article, base_texts, start=10, length=5)
    print(len(out), "revisions reconstructed")
