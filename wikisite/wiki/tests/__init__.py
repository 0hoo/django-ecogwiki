import random
from django.test import TestCase
from ..models import WikiPage


class WikiTestCase(TestCase):

    def update_page(self, content, title=None):
        if title is None:
            title = u'Temp_%d' % int(random.random() * 10000000)
        page = WikiPage.get_by_title(title)
        page.update_content(content, page.revision, user=None)
        return page

    def get_cur_user(self):
        return None