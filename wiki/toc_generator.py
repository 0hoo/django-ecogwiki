# -*- coding: utf-8 -*-
import re
import hashlib


class TocGenerator(object):
    re_headings = ur'<h(\d)\b[^>]*>(.+?)</h\d>'

    def __init__(self, html):
        self._html = html
        self._index = 0

    def validate(self):
        return not self.is_invalid()

    def is_invalid(self):
        try:
            headings = TocGenerator.extract_headings(self._html)
            outlines = self.generate_outline(headings)
            self.generate_path(outlines)
            return False
        except ValueError as e:
            return e.message

    def add_toc(self):
        """Add table of contents to HTML"""
        headings = TocGenerator.extract_headings(self._html)
        outlines = self.generate_outline(headings)
        paths = self.generate_path(outlines)

        if len(headings) > 4:
            toc = u'<div class="toc"><h1>Table of Contents</h1>' \
                  u'%s</div>' % self._generate_toc(outlines, iter(paths))
        else:
            toc = u''

        def replacer(m):
            lev = m.group(1)
            text = m.group(2)
            hashed = TocGenerator.hash_str(paths[self._index])
            html = u'<h%s>%s ' \
                   u'<a id="h_%s" href="#h_%s" class="caret-target">#</a>' \
                   u'</h%s>' % (lev, text, hashed, hashed, lev)

            # insert table of contents before first heading
            if self._index == 0:
                html = toc + html

            self._index += 1
            return html

        return re.sub(TocGenerator.re_headings, replacer, self._html)

    @staticmethod
    def extract_headings(html):
        matches = re.findall(TocGenerator.re_headings, html, flags=re.DOTALL)
        return [(int(m[0]), m[1]) for m in matches]

    @staticmethod
    def hash_str(path):
        m = hashlib.md5()
        m.update(path.encode('utf-8'))
        return m.hexdigest()

    def generate_outline(self, headings):
        """Generate recursive array of document headings"""
        if len(headings) == 0:
            return []

        cur_lev = headings[0][0]
        if cur_lev != 1:
            raise ValueError('Headings should start from H1 but found: <H%d>%s</H%d>' % (cur_lev, headings[0][1], cur_lev))

        _, result = self._outline_children(headings, 0, cur_lev)
        return result

    def _generate_toc(self, outline, path_iter):
        if len(outline) == 0:
            return u''

        parts = [u'<ol>']
        for title, children in outline:
            hashed = TocGenerator.hash_str(path_iter.next())
            title = re.sub(ur'<[^>]+>', '', title)
            parts.append(u'<li>')
            parts.append(u'<div><a href="#h_%s">%s</a></div>' % (hashed, title))
            parts.append(self._generate_toc(children, path_iter))
            parts.append(u'</li>')
        parts.append(u'</ol>')

        return u''.join(parts)

    def _outline_children(self, hs, index, lev):
        result = []
        while len(hs) > index:
            curlev, curtitle = hs[index]
            if curlev == lev:
                index, children = self._outline_children(hs, index + 1, curlev + 1)
                result.append([curtitle, children])
                index += 1
            elif curlev < lev:
                index -= 1
                break
            else:
                raise ValueError('Invalid level of headings: expected H%d or H%d but found <H%d>%s</H%d>' % (lev-1, lev, curlev, curtitle, curlev))

        return index, result

    def generate_path(self, outlines):
        result = []
        self._generate_children_path(result, None, outlines)
        duplicates = {x for x in result if result.count(x) > 1}
        if len(duplicates) > 0:
            raise ValueError("Duplicate paths not allowed: %s" % duplicates.pop())

        return result

    def _generate_children_path(self, result, path, outlines):
        for h, children in outlines:
            if path is not None:
                cur_path = u'%s\t%s' % (path, h)
            else:
                cur_path = h
            result.append(cur_path)
            self._generate_children_path(result, cur_path, children)