import random
from django.test import TestCase
from ..models import WikiPage
from django.contrib.auth.models import User


class WikiTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='0hoo', email='0hoo@0hoo.com', password='0hoo')

    def login(self, username, password, page):
        pass

    def update_page(self, content, title=None):
        if title is None:
            title = u'Temp_%d' % int(random.random() * 10000000)
        page = WikiPage.get_by_title(title)
        page.set_cur_user(self.get_cur_user())
        page.update_content(content, page.revision, user=self.get_cur_user())
        return page

    def get_cur_user(self):
        return self.user