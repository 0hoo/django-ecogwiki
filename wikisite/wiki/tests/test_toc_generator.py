# -*- coding: utf-8 -*-
import re
from django.test import TestCase
from ..toc_generator import TocGenerator


class OutlinerTest(TestCase):
    def setUp(self):
        self.t = TocGenerator('')

    def test_no_headings(self):
        actual = self.t.generate_outline([])
        expected = []
        self.assertEqual(expected, actual)

    def test_single_level(self):
        actual = self.t.generate_outline([
            [1, u'T1'],
            [1, u'T2'],
        ])
        expected = [
            [u'T1', []],
            [u'T2', []],
        ]
        self.assertEqual(expected, actual)

    def test_multi_level_case_1(self):
        actual = self.t.generate_outline([
            [1, u'T1'],
            [1, u'T2'],
            [2, u'T2-1'],
            [2, u'T2-2'],
            [1, u'T3'],
        ])
        expected = [
            [u'T1', []],
            [u'T2', [
                [u'T2-1', []],
                [u'T2-2', []],
            ]],
            [u'T3', []],
        ]
        self.assertEqual(expected, actual)

    def test_multi_level_case_2(self):
        actual = self.t.generate_outline([
            [1, u'T1'],
            [2, u'T1-1'],
            [3, u'T1-1-1'],
            [3, u'T1-1-2'],
            [1, u'T2'],
        ])
        expected = [
            [u'T1', [
                [u'T1-1', [
                    [u'T1-1-1', []],
                    [u'T1-1-2', []],
                ]],
            ]],
            [u'T2', []],
        ]
        self.assertEqual(expected, actual)

    def test_invalid_level(self):
        self.assertRaises(ValueError, self.t.generate_outline, [[1, u'T1'], [3, u'T2']])
        self.assertRaises(ValueError, self.t.generate_outline, [[2, u'T1'], [3, u'T2']])


class PathTest(TestCase):
    def setUp(self):
        self.t = TocGenerator('')

    def test_single_level(self):
        actual = self.t.generate_path([
            [u'제목1', []],
            [u'제목2', []],
        ])
        expected = [
            u'제목1',
            u'제목2',
        ]
        self.assertEqual(expected, actual)

    def test_multi_level(self):
        actual = self.t.generate_path([
            [u'T1', []],
            [u'제목2', [
                [u'제목2-1', []],
                [u'제목2-2', [
                    [u'제목2-2-1', []],
                ]],
            ]],
            [u'T3', []],
        ])
        expected = [
            u'T1',
            u'제목2',
            u'제목2\t제목2-1',
            u'제목2\t제목2-2',
            u'제목2\t제목2-2\t제목2-2-1',
            u'T3',
        ]
        self.assertEqual(expected, actual)

    def test_duplicated_path(self):
        self.assertRaises(ValueError, self.t.generate_path, [[u'T1', []], [u'T1', []]])


class ExtractHeadingsTest(TestCase):
    def test_header_with_attributes(self):
        html = '''
        <h1>a one</h1>
        <h1 id="user-defined-id">a two</h1>
        <h1>a three</h1>
        '''
        headings = TocGenerator.extract_headings(html)
        self.assertEqual(len(headings), 3)


class HTMLGenerationTest(TestCase):
    def test_strip_html_in_headings(self):
        html = """
        <h1><a href="Blah">Hello 1</a></h1>
        <h1>Hello 2</h1>
        <h1>Hello 3</h1>
        <h1>Hello 4</h1>
        """
        t = TocGenerator(html)
        self.assertEqual(1, len(re.findall(ur'Blah', t.add_toc())))


class ValidateTest(TestCase):
    def test_duplicate_path_name_should_mention_reason(self):
        html = '''
            <h1>a one</h1>
            <h1>a two</h1>
            <h1>a one</h1>
            <h1>two</h1>
            <h1>three</h1>
        '''
        reason = TocGenerator(html).is_invalid()
        self.assertIn('a one', reason)

    def test_invalid_level_of_headings_should_mention_reason(self):
        html = '''
            <h1>one</h1>
            <h1>two</h1>
            <h3>three</h3>
        '''
        reason = TocGenerator(html).is_invalid()
        self.assertIn('<h3>three</h3>', reason.lower())

    def test_heading_not_startig_from_h1_should_mention_reason(self):
        html = '''
            <h2>two</h2>
            <h3>three</h3>
        '''
        reason = TocGenerator(html).is_invalid()
        self.assertIn('<h2>two</h2>', reason.lower())