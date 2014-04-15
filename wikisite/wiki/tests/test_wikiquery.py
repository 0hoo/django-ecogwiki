from django.test import TestCase
from ..models import WikiPage
from . import WikiTestCase
from ..search import parse_wikiquery as p


class ParserTest(TestCase):
    def test_simplist_expression(self):
        self.assertEqual([['name', 'A'], ['name']], p('name:"A" > name'))
        self.assertEqual([['name', 'A'], ['name']], p('name:"A"'))
        self.assertEqual([['name', 'A'], ['name']], p('"A"'))

    def test_logical_expression(self):
        self.assertEqual([[['name', 'A'], '*', ['name', 'B']], ['name']],
                         p('"A" * "B"'))
        self.assertEqual([[['name', 'A'], '+', ['name', 'B']], ['name']],
                         p('"A" + "B"'))
        self.assertEqual([[['name', 'A'], '+', [['name', 'B'], '*', ['name', 'C']]], ['name']],
                         p('"A" + "B" * "C"'))
        self.assertEqual([[[['name', 'A'], '+', ['name', 'B']], '*', ['name', 'C']], ['name']],
                         p('("A" + "B") * "C"'))

    def test_attr_expression(self):
        self.assertEqual([['name', 'A'], ['name', 'author']], p('name:"A" > name, author'))


class EvaluationTest(WikiTestCase):
    def setUp(self):
        super(EvaluationTest, self).setUp()
        self.update_page(u'.schema Book\n[[author::Daniel Dennett]] and [[author::Douglas Hofstadter]]\n[[datePublished::1982]]', u'The Mind\'s I')
        self.update_page(u'.schema Book\n{{author::Douglas Hofstadter}}\n[[datePublished::1979]]', u'GEB')
        self.update_page(u'.schema Person', u'Douglas Hofstadter')

    def test_by_name(self):
        self.assertEqual({u'name': u'GEB'}, WikiPage.wikiquery(u'"GEB"'))

    def test_by_schema(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Thing/CreativeWork/Book/"'))

    def test_by_abbr_schema(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Book"'))

    def test_by_attr(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'author:"Douglas Hofstadter"'))

    def test_specifying_attr(self):
        result = WikiPage.wikiquery(u'"GEB" > author')
        self.assertEqual(u'Douglas Hofstadter', result['author'].pvalue)

        result = WikiPage.wikiquery(u'"GEB" > name, author, datePublished')
        self.assertEqual(u'Douglas Hofstadter', result['author'].pvalue)
        self.assertEqual(u'GEB', result['name'].pvalue)
        self.assertEqual(u'1979', result['datePublished'].pvalue)

    def test_logical_operations(self):
        self.assertEqual([{u'name': u'The Mind\'s I'}, {u'name': u'GEB'}],
                         WikiPage.wikiquery(u'"GEB" + "The Mind\'s I"'))
        self.assertEqual({u'name': u'The Mind\'s I'},
                         WikiPage.wikiquery(u'schema:"Book" * author:"Douglas Hofstadter" * author:"Daniel Dennett"'))
        self.assertEqual([{'name': u"The Mind's I"}, {'name': u'GEB'}],
                         WikiPage.wikiquery(u'schema:"Book" + author:"Douglas Hofstadter" * author:"Daniel Dennett"'))

    def test_complex(self):
        result = WikiPage.wikiquery(u'schema:"Thing/CreativeWork/Book/" > name, author')
        self.assertEqual([u'Daniel Dennett', u'Douglas Hofstadter'], [v.pvalue for v in result[0]['author']])
        self.assertEqual(u'The Mind\'s I', result[0]['name'].pvalue)
        self.assertEqual(u'Douglas Hofstadter', result[1]['author'].pvalue)
        self.assertEqual(u'GEB', result[1]['name'].pvalue)
