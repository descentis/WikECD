"""
WikECD (Wikipedia Efficient Compression & Decompression)

High-level convenience API re-export.
"""
from .sources.base import Revision, RevisionSource
from .sources.xml_parser import XMLDumpSource
from .sources.api_client import MediaWikiAPISource
from .compression.compressor import compress_article
from .storage.compressed_store import CompressedArticle
from .retrieval.retrieval import retrieve_range

__version__ = "0.1.1"