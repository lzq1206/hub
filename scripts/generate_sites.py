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
EXCLUDED_REPOS = {"family", "hub"}
PREVIEW_REPO_BASE = "https://raw.githubusercontent.com/lzq1206/hub-previews/main/screenshots"
# GitHub username constraints: starts with alnum, continues with alnum/_/-, max 39 chars.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,38})$")
# Matches owner/repo where both parts are alnum-bounded and can contain underscores/hyphens in-between.
REPO_FULL_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?/[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?$"
)


@dataclass
class Site:
    name: str
    url: str
    description: str
    updated_at: dt.datetime | None


def _is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _pages_url(username: str, repo_name: str) -> str:
    if repo_name.lower() == f"{username.lower()}.github.io":
        return f"https://{username}.github.io/"
    return f"https://{username}.github.io/{quote(repo_name, safe='')}/"


def _site_slug(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "site").replace("www.", "")
    path = parsed.path.strip("/")
    if path:
        path = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
        return f"{host.replace('.', '-')}-{path}".lower()
    return host.replace('.', '-').lower()


def _validate_username(username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Invalid GitHub username format")


def _parse_updated_at(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def _validate_repo_full_name(full_name: str) -> None:
    if not REPO_FULL_NAME_PATTERN.fullmatch(full_name):
        raise ValueError(f"Invalid repo full name format: {full_name}")


def _extract_repo_owner(repo: dict, fallback: str) -> str:
    owner = repo.get("owner")
    if isinstance(owner, dict):
        login = str(owner.get("login", "")).strip()
        if login:
            return login
    return fallback


def _extract_site(pages_owner: str, repo: dict) -> Site | None:
    repo_name = str(repo.get("name", "")).strip().lower()
    if repo_name in EXCLUDED_REPOS:
        return None

    homepage = (repo.get("homepage") or "").strip()
    has_pages = bool(repo.get("has_pages"))

    if _is_http_url(homepage):
        url = homepage
    elif has_pages:
        url = _pages_url(pages_owner, repo.get("name", ""))
    else:
        return None

    description = (repo.get("description") or "").strip() or "暂无介绍"
    return Site(
        name=repo.get("name", "unknown"),
        url=url,
        description=description,
        updated_at=_parse_updated_at(repo.get("updated_at")),
    )


def _request_json(url: str, token: str | None) -> list[dict]:
    if not url.startswith(f"{API_BASE}/users/"):
        raise ValueError("Only GitHub users API URLs are allowed")

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hub-site-indexer"}
    if token:
        headers["Authorization"] = "Bearer " + token

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_repo(full_name: str, token: str | None) -> dict:
    _validate_repo_full_name(full_name)

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hub-site-indexer"}
    if token:
        headers["Authorization"] = "Bearer " + token

    request = Request(f"{API_BASE}/repos/{full_name}", headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_extra_repos(value: str | None) -> list[str]:
    if not value:
        return []
    repos: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        full_name = item.strip()
        if not full_name or full_name in seen:
            continue
        _validate_repo_full_name(full_name)
        repos.append(full_name)
        seen.add(full_name)
    return repos


def fetch_sites(
    username: str,
    token: str | None = None,
    extra_repos: Iterable[str] | None = None,
) -> list[Site]:
    _validate_username(username)
    sites: list[Site] = []
    seen: set[str] = set()
    seen_repos: set[str] = set()
    page = 1

    while True:
        repos = _request_json(
            f"{API_BASE}/users/{username}/repos?per_page=100&page={page}&type=owner&sort=updated",
            token,
        )
        if not repos:
            break

        for repo in repos:
            site = _extract_site(_extract_repo_owner(repo, username), repo)
            if not site or site.url in seen:
                continue
            sites.append(site)
            seen.add(site.url)
            seen_repos.add(str(repo.get("full_name", "")).lower())
        page += 1

    for full_name in extra_repos or []:
        if full_name.lower() in seen_repos:
            continue
        repo = _request_repo(full_name, token)
        site = _extract_site(_extract_repo_owner(repo, username), repo)
        if not site or site.url in seen:
            continue
        sites.append(site)
        seen.add(site.url)

    sites.sort(key=_site_sort_key)
    return sites


def _format_site_updated_at(site: Site) -> str:
    if not site.updated_at:
        return "最近更新时间：未知"
    return f"最近更新时间：{site.updated_at.strftime('%Y-%m-%d %H:%M UTC')}"


def _site_sort_key(site: Site) -> tuple[int, float, str]:
    timestamp = site.updated_at.timestamp() if site.updated_at else 0.0
    return (0 if site.updated_at else 1, -timestamp, site.name.lower())


def build_markdown(username: str, sites: Iterable[Site]) -> str:
    _validate_username(username)
    rows: list[str] = []
    for site in sites:
        preview = (
            f"{PREVIEW_REPO_BASE}/{_site_slug(site.url)}.png"
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
                    _format_site_updated_at(site),
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
            f"自动聚合 [@{username}](https://github.com/{username}) 及附加仓库的已部署网站地址、简介与预览。",
            "",
            "截图图片存放在独立仓库：[`hub-previews`](https://github.com/lzq1206/hub-previews)",
            "",
            f"_最后更新：{now}_",
            "",
            "## 网站列表",
            "",
            content,
            "",
        ]
    )


def build_sites_json(sites: Iterable[Site]) -> str:
    payload = [
        {
            "name": site.name,
            "url": site.url,
            "description": site.description,
            "updated_at": site.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if site.updated_at else None,
            "slug": _site_slug(site.url),
            "preview_url": f"{PREVIEW_REPO_BASE}/{_site_slug(site.url)}.png",
        }
        for site in sites
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a website index README from GitHub repos")
    parser.add_argument("--username", default=os.getenv("GITHUB_USERNAME", DEFAULT_USERNAME))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--extra-repos", default=os.getenv("GITHUB_EXTRA_REPOS", ""))
    parser.add_argument("--output", default="README.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sites = fetch_sites(args.username, args.token, parse_extra_repos(args.extra_repos))
    markdown = build_markdown(args.username, sites)
    with open(args.output, "w", encoding="utf-8") as file:
        file.write(markdown)
    with open("sites.json", "w", encoding="utf-8") as file:
        file.write(build_sites_json(sites))


if __name__ == "__main__":
    main()
