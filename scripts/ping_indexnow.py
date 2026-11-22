#!/usr/bin/env python3
"""Submit PsyPrac URLs to IndexNow (Bing, Yandex, Seznam, Naver).

The key file must already be deployed at KEY_LOCATION; IndexNow validates it
before accepting the URLs. Run this after a production deploy:

    python scripts/ping_indexnow.py
    python scripts/ping_indexnow.py https://www.psyprac.com/ https://www.psyprac.com/login

Google does not use IndexNow; submit sitemap.xml in Google Search Console.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

HOST = "www.psyprac.com"
KEY = "a3a0ba739046ea2ca6bcb318cfa66ca4"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
DEFAULT_URLS = [f"https://{HOST}/"]


def main() -> int:
    urls = sys.argv[1:] or DEFAULT_URLS
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"IndexNow accepted {len(urls)} URL(s): HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        print(f"IndexNow rejected the request: HTTP {exc.code} {exc.reason}")
        print(exc.read().decode("utf-8", errors="replace")[:500])
        return 1
    except urllib.error.URLError as exc:
        print(f"IndexNow request failed: {exc.reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
