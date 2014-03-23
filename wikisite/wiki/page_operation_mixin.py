# -*- coding: utf-8 -*-
import re
import yaml
import operator
import urllib2
import schema
from collections import OrderedDict
import markdown
from yaml.parser import ParserError
from markdown.extensions.def_list import DefListExtension
from markdown.extensions.attr_list import AttrListExtension
from markdownext import md_url, md_wikilink, md_itemprop, md_mathjax, md_strikethrough, md_tables, md_partials, \
    md_section, md_embed
from utils import merge_dicts, pairs_to_dict
from toc_generator import TocGenerator

md = markdown.Markdown(
    extensions=[
        md_wikilink.WikiLinkExtension(),
        md_itemprop.ItemPropExtension(),
        md_url.URLExtension(),
        md_mathjax.MathJaxExtension(),
        md_strikethrough.StrikethroughExtension(),
        md_partials.PartialsExtension(),
        md_tables.TableExtension(),
        md_section.SectionExtension(),
        md_embed.EmbedExtension(),
        DefListExtension(),
        AttrListExtension(),
    ],
    safe_mode=False,
    smart_emphasis=False,
)


class PageOperationMixin(object):
    re_img = re.compile(ur'<(.+?)>[\n\t\s]*<img( .+? )/>[\n\t\s]*</(.+?)>')
    re_metadata = re.compile(ur'^\.([^\s]+)(\s+(.+))?$')
    re_data = re.compile(ur'({{|\[\[)(?P<name>[^\]}]+)::(?P<value>[^\]}]+)(}}|\]\])')
    re_yaml_schema = re.compile(ur'(?:\s{4}|\t)#!yaml/schema[\n\r]+(((?:\s{4}|\t).+[\n\r]+?)+)')
    re_conflicted = re.compile(ur'<<<<<<<.+=======.+>>>>>>>', re.DOTALL)
    re_special_titles_years = re.compile(ur'^(10000|\d{1,4})( BCE)?$')
    re_special_titles_dates = re.compile(ur'^((?P<month>January|February|March|'
                                         ur'April|May|June|July|August|'
                                         ur'September|October|November|'
                                         ur'December)( (?P<date>[0123]?\d))?)$')

    def __init__(self):
        self.cur_user = None

    def set_cur_user(self, user):
        self.cur_user = user

    @property
    def modifier_type(self):
        if self.modifier is None:
            return 'anonymous'

        if self.cur_user is None:
            return 'other'
        elif self.cur_user.email == self.modifier.email:
            return 'self'
        else:
            return 'other'

    @property
    def hashbangs(self):
        return PageOperationMixin.extract_hashbangs(self.rendered_body)


    @staticmethod
    def extract_hashbangs(html):
        matches = re.findall(ur'<code>#!(.+?)[\n;]', html)
        if re.match(ur'.*(\\\(.+\\\)|\$\$.+\$\$)', html, re.DOTALL):
            matches.append('mathjax')
        return matches

    @classmethod
    def path_to_title(cls, path):
        return urllib2.unquote(path).decode('utf-8').replace('_', ' ')

    @property
    def special_sections(self):
        ss = {}

        if self._check_special_titles_years():
            ss[u'years'] = self._special_titles_years()
        elif self._check_special_titles_dates():
            ss[u'dates'] = self._special_titles_dates()

        return ss

    def _check_special_titles_years(self):
        return (
            self.title != '0' and
            re.match(PageOperationMixin.re_special_titles_years, self.title)
        )

    def _check_special_titles_dates(self):
        return (
            re.match(PageOperationMixin.re_special_titles_dates, self.title)
        )

    def _special_titles_years(self):
        ss = {}

        # years: list year titles
        if self.title.endswith(' BCE'):
            cur_year = -int(self.title[:-4]) + 1
        else:
            cur_year = int(self.title)

        years = range(cur_year - 3, cur_year + 4)
        year_titles = []
        for year in years:
            if year < 1:
                year_titles.append(str(abs(year - 1)) + u' BCE')
            else:
                year_titles.append(str(year))

        ss[u'title'] = 'Years'
        ss[u'years'] = year_titles
        ss[u'cur_year'] = str(cur_year)
        return ss

    def _special_titles_dates(self):
        ss = {}

        # dates: list of dates in month
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November',
                       'December']
        m = re.match(PageOperationMixin.re_special_titles_dates, self.title)
        month = m.group('month')
        max_date = 31
        if month == 'February':
            max_date = 29
        elif month in ('April', 'June', 'September', 'November'):
            max_date = 30
        ss[u'title'] = month
        ss[u'month'] = month
        ss[u'prev_month'] = month_names[month_names.index(month) - 1]
        ss[u'next_month'] = month_names[(month_names.index(month) + 1) %
                                        len(month_names)]
        if m.group('date'):
            ss[u'cur_date'] = int(m.group('date'))

        ss[u'dates'] = range(1, max_date + 1)
        return ss

    @property
    def metadata(self):
        return PageOperationMixin.parse_metadata(self.body)

    @classmethod
    def parse_metadata(cls, body):
        # extract lines
        matches = []
        for line in body.split(u'\n'):
            m = re.match(cls.re_metadata, line.strip())
            if m:
                matches.append(m)
            else:
                break
        # default values
        metadata = {
            'content-type': 'text/x-markdown',
            'schema': 'Article',
        }

        # parse
        for m in matches:
            key = m.group(1).strip()
            value = m.group(3)
            metadata[key] = value.strip() if value else None

        # validate
        if u'pub' in metadata and u'redirect' in metadata:
            raise ValueError('You cannot use "pub" and "redirect" metadata at '
                             'the same time.')
        if u'redirect' in metadata and len(PageOperationMixin.remove_metadata(body).strip()) != 0:
            raise ValueError('Page with "redirect" metadata cannot have a body '
                             'content.')
        if u'read' in metadata and metadata['content-type'] != 'text/x-markdown':
            raise ValueError('You cannot restrict read access of custom content-typed page.')

        # done
        return metadata

    @classmethod
    def parse_data(cls, title, body, itemtype=u'Article'):
        # collect data
        default_data = {'name': title, 'schema': schema.get_itemtype_path(itemtype)}
        yaml_data = cls.parse_schema_yaml(body)
        body_data = pairs_to_dict((m.group('name'), m.group('value')) for m in re.finditer(cls.re_data, body))
        data = merge_dicts([default_data, yaml_data, body_data])

        # validation and type conversion
        typed = schema.SchemaConverter.convert(itemtype, data)

        return typed

    @property
    def data(self):
        return PageOperationMixin.parse_data(self.title, self.body, self.itemtype)

    @classmethod
    def parse_schema_yaml(cls, body):
        data = {}

        # extract yaml
        m = re.search(cls.re_yaml_schema, body)
        if not m:
            return data

        # parse
        try:
            parsed = yaml.load(m.group(1))
        except ParserError as e:
            raise ValueError(e)

        # check if it's dict
        if type(parsed) != dict:
            raise ValueError('YAML must be a dictionary')

        return parsed

    @staticmethod
    def title_to_path(path):
        return urllib2.quote(path.replace(u' ', u'_').encode('utf-8'))

    @property
    def paths(self):
        abs_path = []
        result = []
        for token in self.title.split(u'/'):
            abs_path.append(token)
            result.append((u'/'.join(abs_path), token))
        return result

    @property
    def last_path_token(self):
        return self.paths[-1][1]

    @property
    def paths_except_last(self):
        return self.paths[:-1]

    @staticmethod
    def make_description(body, max_length=200):
        # remove yaml/schema block and metadata
        body = re.sub(PageOperationMixin.re_yaml_schema, u'\n', body)
        body = PageOperationMixin.remove_metadata(body).strip()

        # try newline
        index = body.find(u'\n')
        if index != -1:
            body = body[:index].strip()

        # try period
        index = 0
        while index < max_length:
            next_index = body.find(u'. ', index)
            if next_index == -1:
                break
            index = next_index + 1

        if index > 3:
            return body[:index].strip()

        if len(body) <= max_length:
            return body

        # just cut-off
        return body[:max_length - 3].strip() + u'...'

    @staticmethod
    def remove_metadata(body):
        rest = []
        lines = iter(body.split(u'\n'))

        for line in lines:
            m = re.match(PageOperationMixin.re_metadata, line.strip())
            if m is None:
                rest.append(line)
                break

        rest += list(lines)
        return u'\n'.join(rest)


    @property
    def rendered_data(self):
        data = [(n, v, schema.humane_property(self.itemtype, n)) for n, v in self.data.items() if n != 'schema']

        if len(data) == 1:
            # only name and schema?
            return ''

        html = [
            u'<div class="structured-data">',
            u'<h1>Structured data</h1>',
            u'<dl>',
        ]

        data = sorted(data, key=operator.itemgetter(2))

        render_data_item = lambda itemname, itemvalue: \
            u'<dd class="value value-%s"><span itemprop="%s">%s</span></dd>' % (itemname, itemname, itemvalue.render())
        for name, value, humane_name in data:
            html.append(u'<dt class="key key-%s">%s</dt>' % (name, humane_name))
            if type(value) == list:
                html += [render_data_item(name, v) for v in value]
            else:
                html.append(render_data_item(name, value))
        html.append(u'</dl></div>')
        return '\n'.join(html)

    @property
    def rendered_body(self):
        return PageOperationMixin.render_body(
            self.title, self.body, self.rendered_data, self.inlinks, self.related_links_by_score)

    @classmethod
    def render_body(cls, title, body, rendered_data='', inlinks={}, related_links_by_score={}, older_title=None, newer_title=None):
        # body
        body_parts = [cls.remove_metadata(body)]

        # incoming links
        if len(inlinks) > 0:
            lines = [u'# Incoming Links']
            for rel, links in inlinks.items():
                itemtype, rel = rel.split('/')
                lines.append(u'## %s' % schema.humane_property(itemtype, rel, True))
                # remove dups and sort
                links = list(set(links))
                links.sort()

                lines += [u'* [[%s]]' % t for t in links]
            body_parts.append(u'\n'.join(lines))

        # related links
        related_links = related_links_by_score
        if len(related_links) > 0:
            lines = [u'# Suggested Pages']
            lines += [u'* {{.score::%.3f}} [[%s]]\n{.noli}' % (score, t)
                      for t, score in related_links.items()[:10]]
            body_parts.append(u'\n'.join(lines))
            body_parts.append(u'* [More suggestions...](/+%s)\n{.more-suggestions}' % (cls.title_to_path(title)))

        # remove yaml/schema block
        joined = u'\n'.join(body_parts)
        joined = re.sub(PageOperationMixin.re_yaml_schema, u'\n', joined)

        # render to html
        rendered = md.convert(joined)

        # add table of contents
        rendered = TocGenerator(rendered).add_toc()

        # add class for embedded image
        rendered = PageOperationMixin.re_img.sub(ur'<\1 class="img-container"><img\2/></\3>', rendered)

        # add structured data block
        rendered = rendered_data + rendered

        return rendered
        #cls.sanitize_html(rendered)

    @property
    def itemtype(self):
        if 'schema' in self.metadata:
            return self.metadata['schema']
        else:
            return u'Article'

    @property
    def related_links_by_score(self):
        sorted_tuples = sorted(self.related_links.iteritems(),
                               key=operator.itemgetter(1),
                               reverse=True)
        return OrderedDict(sorted_tuples)

    @property
    def related_links_by_title(self):
        sorted_tuples = sorted(self.related_links.iteritems(),
                               key=operator.itemgetter(0))
        return OrderedDict(sorted_tuples)

    @property
    def itemtype_url(self):
        return 'http://schema.org/%s' % self.itemtype

    def can_read(self, user, default_acl=None, acl_r=None, acl_w=None):
        return True

    def can_write(self, user, default_acl=None, acl_r=None, acl_w=None):
        return False