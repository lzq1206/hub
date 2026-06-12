#!/usr/bin/env python3
"""Generate README for deployed websites under a GitHub user."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


API_BASE = "https://api.github.com"
DEFAULT_USERNAME = "lzq1206"
# GitHub username constraints: starts with alnum, continues with alnum/_/-, max 39 chars.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,38})$")


@dataclass
class Site:
    name: str
    url: str
    description: str


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _pages_url(username: str, repo_name: str) -> str:
    if repo_name.lower() == f"{username.lower()}.github.io":
        return f"https://{username}.github.io/"
    return f"https://{username}.github.io/{quote(repo_name, safe='')}/"


def _validate_username(username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Invalid GitHub username format")


def _extract_site(username: str, repo: dict) -> Site | None:
    homepage = (repo.get("homepage") or "").strip()
    has_pages = bool(repo.get("has_pages"))

    if _is_http_url(homepage):
        url = homepage
    elif has_pages:
        url = _pages_url(username, repo.get("name", ""))
    else:
        return None

    description = (repo.get("description") or "").strip() or "暂无介绍"
    return Site(name=repo.get("name", "unknown"), url=url, description=description)


def _request_json(url: str, token: str | None) -> list[dict]:
    if not url.startswith(f"{API_BASE}/users/"):
        raise ValueError("Only GitHub users API URLs are allowed")

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hub-site-indexer"}
    if token:
        headers["Authorization"] = "Bearer " + token

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_sites(username: str, token: str | None = None) -> list[Site]:
    _validate_username(username)
    sites: list[Site] = []
    seen: set[str] = set()
    page = 1

    while True:
        repos = _request_json(
            f"{API_BASE}/users/{username}/repos?per_page=100&page={page}&type=owner&sort=updated",
            token,
        )
        if not repos:
            break

        for repo in repos:
            site = _extract_site(username, repo)
            if not site or site.url in seen:
                continue
            sites.append(site)
            seen.add(site.url)
        page += 1

    sites.sort(key=lambda item: item.name.lower())
    return sites


def build_markdown(username: str, sites: Iterable[Site]) -> str:
    _validate_username(username)
    rows: list[str] = []
    for site in sites:
        preview = (
            f"https://image.thum.io/get/width/640/noanimate/{quote(site.url, safe='')}"
            if _is_http_url(site.url)
            else None
        )
        rows.append(
            "\n".join(
                [
                    f"### [{site.name}]({site.url})",
                    "",
                    site.description,
                    "",
                    f"![{site.name} 预览图]({preview})" if preview else "预览不可用",
                    "",
                ]
            )
        )

    content = "\n".join(rows) if rows else "暂未发现已部署的网站。"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return "\n".join(
        [
            "# hub",
            "",
            f"自动聚合 [@{username}](https://github.com/{username}) 的已部署网站地址、简介与预览。",
            "",
            f"_最后更新：{now}_",
            "",
            "## 网站列表",
            "",
            content,
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a website index README from GitHub repos")
    parser.add_argument("--username", default=os.getenv("GITHUB_USERNAME", DEFAULT_USERNAME))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--output", default="README.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sites = fetch_sites(args.username, args.token)
    markdown = build_markdown(args.username, sites)
    with open(args.output, "w", encoding="utf-8") as file:
        file.write(markdown)


if __name__ == "__main__":
    main()
