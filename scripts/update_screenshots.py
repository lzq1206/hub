#!/usr/bin/env python3
"""Manually refresh website screenshots listed in README."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


SECTION_PATTERN = re.compile(
    r"### \[[^\]]+\]\((?P<url>https?://[^)]+)\).*?!\[[^\]]+\]\([^)]*/screenshots/(?P<file>[^)]+)\)",
    re.S,
)


def parse_targets(readme_path: Path) -> list[tuple[str, str]]:
    content = readme_path.read_text(encoding="utf-8")
    return [(m.group("url"), m.group("file")) for m in SECTION_PATTERN.finditer(content)]


def refresh_screenshots(
    targets: list[tuple[str, str]],
    output_dir: Path,
    width: int,
    height: int,
    wait_ms: int,
    timeout_ms: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    updated = 0
    failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height}, ignore_https_errors=True)
        page = context.new_page()
        for url, filename in targets:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except PlaywrightTimeoutError:
                    pass
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(output_dir / filename), full_page=True)
                updated += 1
                print(f"updated {filename} <- {url}")
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{url}: {exc}")
                print(f"failed {filename} <- {url}: {exc}")
        context.close()
        browser.close()
    if failures:
        print("\nfailed targets:")
        for item in failures:
            print(f"- {item}")
    if updated == 0:
        raise RuntimeError("No screenshots were updated.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manually refresh README website screenshots.")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--screenshots-dir", default="screenshots")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--wait-ms", type=int, default=5000, help="Extra wait after page load.")
    parser.add_argument("--timeout-ms", type=int, default=120000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = parse_targets(Path(args.readme))
    if not targets:
        raise ValueError("No screenshot targets found in README.")
    refresh_screenshots(
        targets=targets,
        output_dir=Path(args.screenshots_dir),
        width=args.width,
        height=args.height,
        wait_ms=args.wait_ms,
        timeout_ms=args.timeout_ms,
    )


if __name__ == "__main__":
    main()
