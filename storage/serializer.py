from __future__ import annotations
import json, gzip
from typing import Dict, Any
from .compressed_store import CompressedArticle

def dumps(article: CompressedArticle, base_texts: Dict[int, str] | None = None) -> bytes:
    payload: Dict[str, Any] = {
        "title": article.title,
        "anchors": article.anchors,
        "patches": {f"{u}-{v}": p for (u, v), p in article.patches.items()},
        "meta": article.meta,
        "base_texts": base_texts or {},  # optional embed
    }
    return gzip.compress(json.dumps(payload).encode("utf-8"))

def loads(blob: bytes) -> tuple[CompressedArticle, Dict[int, str]]:
    obj = json.loads(gzip.decompress(blob).decode("utf-8"))
    patches = {}
    for k, v in obj["patches"].items():
        u, v2 = map(int, k.split("-"))
        patches[(u, v2)] = v
    article = CompressedArticle(
        title=obj["title"], anchors=obj["anchors"], patches=patches, meta=obj.get("meta", {})
    )
    base_texts = {int(k): v for k, v in obj.get("base_texts", {}).items()}
    return article, base_texts

def save(path: str, article: CompressedArticle, base_texts: Dict[int, str] | None = None) -> None:
    with open(path, "wb") as f:
        f.write(dumps(article, base_texts))

def load(path: str) -> tuple[CompressedArticle, Dict[int, str]]:
    with open(path, "rb") as f:
        return loads(f.read())
