import unittest
from unittest import mock

from scripts.generate_sites import (
    Site,
    _build_manual_site,
    _extract_page_metadata,
    _extract_site,
    _pages_url,
    _request_json,
    build_markdown,
    fetch_sites,
    parse_extra_repos,
    parse_manual_sites,
)


class GenerateSitesTests(unittest.TestCase):
    def test_extract_site_prefers_homepage(self):
        repo = {"name": "demo", "homepage": "https://example.com", "has_pages": True, "description": "desc"}
        site = _extract_site("lzq1206", repo)
        self.assertIsNotNone(site)
        self.assertEqual(site.url, "https://example.com")

    def test_extract_site_falls_back_to_pages(self):
        repo = {"name": "demo", "homepage": "", "has_pages": True, "description": ""}
        site = _extract_site("lzq1206", repo)
        self.assertIsNotNone(site)
        self.assertEqual(site.url, "https://lzq1206.github.io/demo/")
        self.assertEqual(site.description, "暂无介绍")

    def test_pages_url_for_user_site(self):
        self.assertEqual(_pages_url("lzq1206", "lzq1206.github.io"), "https://lzq1206.github.io/")

    def test_build_markdown_contains_intro(self):
        markdown = build_markdown("lzq1206", [])
        self.assertIn("自动聚合", markdown)
        self.assertIn("暂未发现已部署的网站", markdown)

    def test_build_markdown_handles_non_http_url_preview(self):
        markdown = build_markdown("lzq1206", [Site(name="local", url="ftp://local", description="desc", updated_at=None)])
        self.assertIn("预览不可用", markdown)
        self.assertIn("最近更新时间：未知", markdown)

    def test_parse_extra_repos_deduplicates_and_strips(self):
        repos = parse_extra_repos(" owner/repo ,owner/repo,foo/bar ")
        self.assertEqual(repos, ["owner/repo", "foo/bar"])

    def test_parse_extra_repos_rejects_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_extra_repos("bad/repo/name")

    def test_parse_extra_repos_rejects_path_traversal_in_repo_name(self):
        with self.assertRaises(ValueError):
            parse_extra_repos("owner/../repo")

    def test_fetch_sites_rejects_invalid_username(self):
        with self.assertRaises(ValueError):
            fetch_sites("bad/name")

    def test_parse_manual_sites_deduplicates_and_filters_invalid_urls(self):
        urls = parse_manual_sites(["https://a.com", "https://a.com", "ftp://bad", ""])
        self.assertEqual(urls, ["https://a.com"])

    def test_extract_page_metadata(self):
        page = '<html><head><title>Demo Site</title><meta name="description" content="Hello world"></head></html>'
        description, title = _extract_page_metadata(page)
        self.assertEqual(description, "Hello world")
        self.assertEqual(title, "Demo Site")

    def test_build_manual_site_uses_auto_description_when_missing(self):
        with mock.patch("scripts.generate_sites._request_text", return_value="<title>My Site</title>"):
            site = _build_manual_site("https://example.com/app/")
        self.assertEqual(site.name, "My Site")
        self.assertEqual(site.description, "My Site 项目主页")

    def test_request_json_rejects_non_github_users_api_url(self):
        with self.assertRaises(ValueError):
            _request_json("https://example.com/repos", None)


if __name__ == "__main__":
    unittest.main()
