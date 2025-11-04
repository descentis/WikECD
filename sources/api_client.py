from __future__ import annotations
from typing import Iterable, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base import Revision, RevisionSource
from time import sleep

DEFAULT_UA = (
    "WikECD/0.1 (+https://example.com/wikecd; contact: your-email@example.com) "
    "python-requests"
)


def _session_with_retries(user_agent: str | None = None) -> requests.Session:
    """
    Return a requests.Session with retry logic.
    Compatible with both older and newer urllib3 versions.
    """
    s = requests.Session()

    # Handle both 'allowed_methods' (new) and 'method_whitelist' (old)
    retry_kwargs = dict(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    try:
        retry = Retry(**retry_kwargs, allowed_methods=["GET"])
    except TypeError:
        retry = Retry(**retry_kwargs, method_whitelist=["GET"])

    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)

    s.headers.update({
        "User-Agent": user_agent or "WikECD/0.1 (+contact: you@example.com)"
    })
    return s


class MediaWikiAPISource(RevisionSource):
    def __init__(
        self,
        api_url: str = "https://en.wikipedia.org/w/api.php",
        session: Optional[requests.Session] = None,
        user_agent: Optional[str] = None,
        verbose: bool = False,                     # <— NEW
        pause_seconds: float = 0.1,                # <— polite short pause between requests
    ):
        self.api_url = api_url
        self.session = session or _session_with_retries(user_agent)
        self.verbose = verbose
        self.pause_seconds = pause_seconds

    def get_revisions(self, *, title: Optional[str] = None, limit: int = 500) -> Iterable[Revision]:
        if not title:
            raise ValueError("title is required for API source")

        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "titles": title,
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "rvlimit": min(limit, 500),
            "rvdir": "newer",
        }

        cont = {}
        yielded = 0
        while True:
            if self.verbose:
                ua = self.session.headers.get("User-Agent", "")
                print(f"[WikECD] GET {self.api_url}  (rvlimit={params['rvlimit']})  UA='{ua}'  cont={cont or '{}'}")

            resp = self.session.get(self.api_url, params={**params, **cont}, timeout=60)

            if self.verbose:
                print(f"[WikECD] HTTP {resp.status_code}")
                # print first 200 chars of body on non-2xx for clues
                if resp.status_code >= 300:
                    print("[WikECD] Body:", resp.text[:200])

            if resp.status_code == 403:
                raise requests.HTTPError(
                    "403 Forbidden from Wikipedia API. Provide a descriptive User-Agent with contact info. "
                    "Use --user-agent in CLI or MediaWikiAPISource(user_agent=...)."
                )

            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", [])
            if self.verbose and not pages:
                print("[WikECD] No pages returned in this batch.")

            for page in pages:
                for rev in page.get("revisions", []):
                    revid = rev["revid"]
                    timestamp = rev["timestamp"]
                    text = rev.get("slots", {}).get("main", {}).get("content", "")
                    yield Revision(revid=revid, timestamp=timestamp, text=text)
                    yielded += 1
                    if yielded >= limit:
                        if self.verbose:
                            print(f"[WikECD] Reached requested limit {limit}.")
                        return

            if "continue" in data and yielded < limit:
                cont = data["continue"]
                if self.verbose:
                    print(f"[WikECD] Continue token: {cont}")
                sleep(self.pause_seconds)
            else:
                if self.verbose:
                    print("[WikECD] Completed without continue.")
                break


def resolve_page_ids(titles: List[str], user_agent: Optional[str] = None) -> Dict[str, int]:
    """
    Resolve titles -> page_ids with normalization + redirects.
    Returns {normalized_title: pageid}
    """
    s = _session_with_retries(user_agent)
    url = "https://en.wikipedia.org/w/api.php"
    out: Dict[str, int] = {}
    BATCH = 50
    for i in range(0, len(titles), BATCH):
        batch = titles[i:i+BATCH]
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(batch),
            "redirects": 1,          # follow redirects
            "converttitles": 1,      # normalize
        }
        resp = s.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            if "missing" in page:
                continue
            title = page["title"]
            out[title] = int(page["pageid"])
    return out

