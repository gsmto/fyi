"""URL regressions: python -m unittest discover -s tests -v"""
import unittest

from scripts.archive import validate_brief


def brief_with_image():
    return {
        'id': 'daily-brief-2026-10-17', 'collectionId': 'daily-brief',
        'date': '2026-10-17', 'title': 'URL validation fixture',
        'summary': '', 'analysis': '', 'rawText': '', 'completeness': 'summary',
        'sourceConversation': 'test', 'provenance': '', 'score': None,
        'items': [{
            'id': 'daily-brief-2026-10-17-item', 'title': 'Item',
            'category': 'test', 'summary': '', 'analysis': '',
            'importance': None, 'tags': [], 'sources': [],
            'images': [{'url': 'https://example.com/image.png', 'alt': 'Image'}],
        }],
    }


class ArchiveURLTests(unittest.TestCase):
    def validate_image_url(self, field, value):
        brief = brief_with_image()
        brief['items'][0]['images'][0][field] = value
        validate_brief(brief, 'daily-brief', '2026-10')

    def test_static_hosts_are_accepted(self):
        for field in ('url', 'sourceUrl'):
            for url in ('https://static.example.com/image.png', 'https://static/image.png'):
                with self.subTest(field=field, url=url):
                    self.validate_image_url(field, url)

    def test_literal_spaces_anywhere_are_rejected(self):
        for field in ('url', 'sourceUrl'):
            for url in (
                'https://exa mple.com/image.png',
                'https://example.com/a b.png',
                'https://example.com/image.png?q=a b',
                'https://example.com/image.png#a b',
                ' https://example.com/image.png',
                'https://example.com/image.png ',
            ):
                with self.subTest(field=field, url=url):
                    with self.assertRaisesRegex(ValueError, 'invalid image (source )?URL'):
                        self.validate_image_url(field, url)

    def test_valid_complete_urls_are_accepted(self):
        for field in ('url', 'sourceUrl'):
            for url in (
                'https://static.example.com:8443/a%20b.png?v=1&size=large#preview',
                'https://example.com',
                'https://example.com./image.png',
                'https://192.0.2.1/image.png',
                'https://[2001:db8::1]:443/image.png',
                'https://例子.测试/图片.png',
                'HTTPS://STATIC.EXAMPLE.COM/image.png',
            ):
                with self.subTest(field=field, url=url):
                    self.validate_image_url(field, url)

    def test_malformed_urls_are_rejected(self):
        for field in ('url', 'sourceUrl'):
            for url in (
                None, 123, '', '//example.com/image.png',
                'javascript:alert(1)', 'ftp://example.com/image.png',
                'https:///image.png', 'https://?q=image',
                'https://example.com:abc/image.png',
                'https://example.com:65536/image.png',
                'https://example.com:/image.png',
                'https://example..com/image.png',
                'https://-example.com/image.png',
                'https://999.0.0.1/image.png',
                'https://[invalid]/image.png',
                'https://[2001:db8::1]garbage/image.png',
                'https://user:secret@example.com/image.png',
                'https://example.com/a\\b.png',
                'https://example.com/a\nb.png',
                'https://example.com/a\tb.png',
                'https://example.com/a\x00b.png',
                'https://example.com/a\x7fb.png',
                'https://example.com/a\u00a0b.png',
                'https://example.com/image.png?q=%ZZ',
                'https://example.com/image.png#bad%',
                'https://example.com/<image>.png',
            ):
                with self.subTest(field=field, url=url):
                    with self.assertRaisesRegex(ValueError, 'invalid image (source )?URL'):
                        self.validate_image_url(field, url)

    def test_scheme_rules(self):
        self.validate_image_url('sourceUrl', 'http://static.example.com/story')
        with self.assertRaisesRegex(ValueError, 'invalid image URL'):
            self.validate_image_url('url', 'http://static.example.com/image.png')

    def test_historical_items_need_no_images(self):
        brief = brief_with_image()
        del brief['items'][0]['images']
        validate_brief(brief, 'daily-brief', '2026-10')

    def test_news_sources_use_complete_url_validation(self):
        brief = brief_with_image()
        source = {'title': 'Source', 'url': 'https://static.example.com/story?q=a%20b'}
        brief['items'][0]['sources'] = [source]
        validate_brief(brief, 'daily-brief', '2026-10')
        source['url'] = 'https://example.com/story?q=a b'
        with self.assertRaisesRegex(ValueError, 'invalid source URL'):
            validate_brief(brief, 'daily-brief', '2026-10')


if __name__ == '__main__':
    unittest.main()
