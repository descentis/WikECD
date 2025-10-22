# tests/test_xml_stream_bz2.py
import bz2, os, tempfile
from WikECD.sources.xml_parser import XMLDumpSource
from WikECD.compression.compressor import compress_article

SAMPLE_XML = """<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/">
  <page>
    <title>WikECD Demo</title>
    <id>123</id>
    <revision>
      <id>1</id>
      <timestamp>2024-01-01T00:00:00Z</timestamp>
      <text>hello</text>
    </revision>
    <revision>
      <id>2</id>
      <timestamp>2024-01-02T00:00:00Z</timestamp>
      <text>hello world</text>
    </revision>
  </page>
</mediawiki>"""

def test_xml_bz2_streaming():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sample.xml.bz2")
        with bz2.open(path, "wt", encoding="utf-8") as f:
            f.write(SAMPLE_XML)

        src = XMLDumpSource(path)
        revs = list(src.get_revisions(title="WikECD Demo"))
        assert len(revs) == 2
        assert revs[0].revid == 1
        assert revs[1].revid == 2

        article = compress_article("WikECD Demo", revs)
        assert article.meta["count"] == 2
        assert len(article.anchors) >= 1
