from django.test import Client
from . import WikiTestCase
from ..models import WikiPage


class ContentTypeTest(WikiTestCase):
    def setUp(self):
        super(ContentTypeTest, self).setUp()
        self.browser = Client()

    def test_get_default_content_type(self):
        self.update_page(u'Hello', u'Test')
        res = self.browser.get('/Test')
        self.assertEqual('text/html; charset=utf-8', res['Content-type'])

    def test_get_json_content_type(self):
        self.update_page(u'Hello', u'Test')
        res = self.browser.get('/Test?_type=json')
        self.assertEqual('application/json; charset=utf-8', res['Content-type'])

    def test_get_custom_content_type(self):
        self.update_page(u'.content-type text/plain\nHello', u'Test')
        res = self.browser.get('/Test')
        self.assertEqual('text/plain; charset=utf-8', res['Content-type'])
        self.assertEqual('Hello', res.content)

    def test_view_should_override_custom_content_type(self):
        self.update_page(u'.content-type text/plain\nHello', u'Test')
        res = self.browser.get('/Test?view=edit')
        self.assertEqual('text/html; charset=utf-8', res['Content-type'])

    def test_should_not_restrict_read_access_to_custom_content_type(self):
        p = WikiPage.get_by_title(u'Test')
        self.assertRaises(ValueError, p.update_content, u'.read ak@gmail.com\n.content-type text/plain\nHello', 0)