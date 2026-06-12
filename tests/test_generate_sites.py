import unittest

from scripts.generate_sites import Site, _extract_site, _pages_url, _request_json, build_markdown, fetch_sites


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
        markdown = build_markdown("lzq1206", [Site(name="local", url="ftp://local", description="desc")])
        self.assertIn("预览不可用", markdown)

    def test_fetch_sites_rejects_invalid_username(self):
        with self.assertRaises(ValueError):
            fetch_sites("bad/name")

    def test_request_json_rejects_non_github_users_api_url(self):
        with self.assertRaises(ValueError):
            _request_json("https://example.com/repos", None)


if __name__ == "__main__":
    unittest.main()
