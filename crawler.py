from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

from utils import SNAPSHOTS_DIR, read_watchlist, snapshot_path, strip_noisy_html, today_iso


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)


@dataclass
class CrawlResult:
    service: str
    url: str
    path: str | None
    status: str
    error: str | None = None


def fetch_url(url: str, timeout: int = 20) -> str:
    try:
        import httpx

        response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except ImportError:
        pass
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status < 200 or status >= 300:
            raise RuntimeError(f"HTTP {status}")
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def crawl(day: str | None = None) -> list[CrawlResult]:
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    day = day or today_iso()
    results: list[CrawlResult] = []

    for service, url in read_watchlist():
        try:
            html = strip_noisy_html(fetch_url(url))
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "noscript", "svg"]):
                    tag.decompose()
                html = str(soup)
            except ImportError:
                pass
            path = snapshot_path(service, day)
            path.write_text(html, encoding="utf-8")
            results.append(CrawlResult(service, url, str(path), "crawled"))
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            results.append(CrawlResult(service, url, None, "failed", str(exc)))
    return results


if __name__ == "__main__":
    for item in crawl():
        detail = f" -> {item.path}" if item.path else f" ({item.error})"
        print(f"{item.service}: {item.status}{detail}")
