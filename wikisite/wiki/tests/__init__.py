import random
from django.test import TestCase
from django.contrib.auth.models import User
from ..models import WikiPage
from .. import caching


class WikiTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username='0hoo', email='0hoo@0hoo.com', password='0hoo')

    def login(self, username, password, page):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_superuser(username=username, email='', password=password)

        if user:
            caching.add_recent_email(user.email)
        page.set_cur_user(user)

    def update_page(self, content, title=None):
        if title is None:
            title = u'Temp_%d' % int(random.random() * 10000000)
        page = WikiPage.get_by_title(title)
        page.set_cur_user(self.get_cur_user())
        page.update_content(content, page.revision, user=self.get_cur_user())
        return page

    def get_cur_user(self):
        return self.user