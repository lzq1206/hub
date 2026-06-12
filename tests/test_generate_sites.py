import unittest

from scripts.generate_sites import _extract_site, _pages_url, build_markdown


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


if __name__ == "__main__":
    unittest.main()
