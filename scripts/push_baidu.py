#!/usr/bin/env python3
"""Push URLs to Baidu's 普通收录 API.

Prerequisites:
  1. The site is verified in 百度搜索资源平台 (https://ziyuan.baidu.com).
  2. 普通收录 -> API 提交 gives you a token.

Usage:
    BAIDU_PUSH_TOKEN=xxxxxxxx python scripts/push_baidu.py
    BAIDU_PUSH_TOKEN=xxxxxxxx python scripts/push_baidu.py https://www.psyprac.com/
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://www.psyprac.com"
ENDPOINT = "https://data.zz.baidu.com/urls"
DEFAULT_URLS = [f"{SITE}/"]


def main() -> int:
    token = os.environ.get("BAIDU_PUSH_TOKEN", "").strip()
    if not token:
        print("Set BAIDU_PUSH_TOKEN (from 百度搜索资源平台 → 普通收录 → API 提交).")
        return 2

    urls = sys.argv[1:] or DEFAULT_URLS
    query = urllib.parse.urlencode({"site": SITE, "token": token})
    request = urllib.request.Request(
        f"{ENDPOINT}?{query}",
        data="\n".join(urls).encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        print(f"Baidu push failed: HTTP {exc.code} {exc.reason}")
        print(exc.read().decode("utf-8", errors="replace")[:500])
        return 1
    except urllib.error.URLError as exc:
        print(f"Baidu push failed: {exc.reason}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
