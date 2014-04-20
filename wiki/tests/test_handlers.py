import re
import lxml.etree
from lxml.html import html5parser
from django.test import Client
from . import WikiTestCase
from ..models import WikiPage


class Browser(Client):
    def __init__(self, enforce_csrf_checks=False, **defaults):
        super(Browser, self).__init__(enforce_csrf_checks, **defaults)
        self.parser = html5parser.HTMLParser(strict=True)
        self.res = None
        self.tree = None

    def get(self, path, data={}, follow=False):
        self.res = super(Browser, self).get(path, data, follow)
        if len(self.res.content) > 0 and self.res['content-type'].split(';')[0].strip() == 'text/html':
            self.tree = html5parser.fromstring(self.res.content, parser=self.parser)
        if follow and self.res.status_code in [301, 302, 303, 304, 307] and 'location' in self.res:
            self.get(self.res['location'][16:])
        return self.res

    def query(self, path):
        return self._query(self.tree, path)

    def _query(self, element, path):
        path = re.sub(r'/(\w+\d?)', r'/html:\1', path)
        return element.findall(path, namespaces={'html': 'http://www.w3.org/1999/xhtml'})


class ContentTypeTest(WikiTestCase):
    def setUp(self):
        super(ContentTypeTest, self).setUp()
        self.browser = Browser()

    def test_get_default_content_type(self):
        self.update_page(u'Hello', u'Test')
        self.browser.get('/Test')
        self.assertEqual('text/html; charset=utf-8', self.browser.res['Content-type'])

    def test_get_json_content_type(self):
        self.update_page(u'Hello', u'Test')
        self.browser.get('/Test?_type=json')
        self.assertEqual('application/json; charset=utf-8', self.browser.res['Content-type'])

    def test_get_custom_content_type(self):
        self.update_page(u'.content-type text/plain\nHello', u'Test')
        self.browser.get('/Test')
        self.assertEqual('text/plain; charset=utf-8', self.browser.res['Content-type'])
        self.assertEqual('Hello', self.browser.res.content)

    def test_view_should_override_custom_content_type(self):
        self.update_page(u'.content-type text/plain\nHello', u'Test')
        self.browser.get('/Test?view=edit')
        self.assertEqual('text/html; charset=utf-8', self.browser.res['Content-type'])

    def test_should_not_restrict_read_access_to_custom_content_type(self):
        p = WikiPage.get_by_title(u'Test')
        self.assertRaises(ValueError, p.update_content, u'.read ak@gmail.com\n.content-type text/plain\nHello', 0)