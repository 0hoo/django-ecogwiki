from . import WikiTestCase
from ..models import WikiPage


class DefaultBlogPublishTest(WikiTestCase):
    def setUp(self):
        super(DefaultBlogPublishTest, self).setUp()

    def test_first_publish(self):
        self.update_page(u'Hello', u'Hello')
        self.assertEqual(0, len(WikiPage.get_posts_of(None)))

        page = self.update_page(u'.pub\nHello', u'Hello')
        self.assertIsNotNone(page.published_at)
        self.assertIsNone(page.published_to)
        self.assertEqual(1, len(WikiPage.get_posts_of(None)))

    def test_second_publish(self):
        page1 = self.update_page(u'.pub\nHello 1')
        page2 = self.update_page(u'.pub\nHello 2')
        posts = WikiPage.get_posts_of(None)
        self.assertEqual(2, len(posts))
        self.assertEqual(page2.title, posts[1].newer_title)
        self.assertEqual(page1.title, posts[0].older_title)


class DefaultBlogUnpublishTest(WikiTestCase):
    def setUp(self):
        super(DefaultBlogUnpublishTest, self).setUp()

        self.update_page(u'.pub\nHello 1', u'Hello 1')
        self.update_page(u'.pub\nHello 2', u'Hello 2')
        self.update_page(u'.pub\nHello 3', u'Hello 3')

    def test_unpublish_middle(self):
        self.update_page(u'Hello 2', u'Hello 2')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)

    def test_unpublish_oldest(self):
        self.update_page(u'Hello 1', u'Hello 1')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 2', newer.older_title)

    def test_unpublish_newest(self):
        self.update_page(u'Hello 3', u'Hello 3')

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 2', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)

    def test_delete_published_page(self):
        page = WikiPage.get_by_title(u'Hello 2')
        user = self.login('a@x.com', 'a', page, is_admin=True)
        page.delete(user)

        newer, older = WikiPage.get_posts_of(None)
        self.assertEqual(u'Hello 3', older.newer_title)
        self.assertEqual(u'Hello 1', newer.older_title)
