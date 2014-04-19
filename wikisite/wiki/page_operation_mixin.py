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
import acl

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
    re_section_data = re.compile(ur'''^(?P<name>[^\s]+?)::---+$''')
    re_yaml_schema = re.compile(ur'''
                                # HEADER
        (?:[ ]{4}|\t)           #   leading tab or 4 space followed by (non-capture)
        \#!yaml/schema          #   `#!yaml/schema`
        \n+                     #   new line(s)
        (                       # CONTENT (group 1)
            (                   #   multiple lines of  (group 2)
                (?:[ ]{4}|\t)   #   leading tab or 4 space followed by (non-capture)
                .+?             #   any string
                \n+             #   new line(s)
            )+
        )
    ''', re.VERBOSE + re.MULTILINE + re.DOTALL)
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
    def absolute_url(self):
        return self.absolute_latest_url

    @property
    def absolute_latest_url(self):
        return u'/%s' % PageOperationMixin.title_to_path(self.title)

    @property
    def revision_list_url(self):
        return u'/%s?rev=list' % PageOperationMixin.title_to_path(self.title)

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
        body = body.replace('\r\n', '\n')

        default_data = {'name': title, 'schema': schema.get_itemtype_path(itemtype)}

        # collect
        yaml_data = cls.parse_schema_yaml(body)
        body_data = pairs_to_dict((m.group('name'), m.group('value')) for m in re.finditer(cls.re_data, body))

        if itemtype == u'Article' or u'Article' in schema.get_schema(itemtype)[u'ancestors']:
            default_section = u'articleBody'
        else:
            default_section = u'longDescription'
        section_data = cls.parse_sections(body, default_section)

        # merge
        data = merge_dicts([default_data, yaml_data, body_data, section_data])

        # validation and type conversion
        typed = schema.SchemaConverter.convert(itemtype, data)

        return typed

    @classmethod
    def parse_sections(cls, body, default_section=u'articleBody'):
        # remove metadata and yaml schema block
        body = cls.remove_metadata(body)
        body = re.sub(PageOperationMixin.re_yaml_schema, u'\n', body).strip()
        lines = body.split('\n')

        # append default section
        if not cls.re_section_data.match(lines[0]):
            lines.insert(0, u'%s::---' % default_section)

        i = 0
        sections = {}
        section_name = None
        section_lines = None

        while i < len(lines):
            m = cls.re_section_data.match(lines[i])
            if m:
                if section_name is None:
                    # Found first section. Start new one
                    section_name = m.group('name')
                    section_lines = []
                else:
                    # Found other section. Close current one and start the new one
                    sections[section_name] = '\n'.join(section_lines).strip()
                    section_name = m.group('name')
                    section_lines = []
            else:
                # In the section. Collect lines
                section_lines.append(lines[i])

            # Remove this line
            lines.pop(i)

        if section_name:
            sections[section_name] = '\n'.join(section_lines).strip()

        return sections


    @property
    def data(self):
        data = PageOperationMixin.parse_data(self.title, self.body, self.itemtype)
        data['datePageModified'] = schema.DateTimeProperty(self.itemtype, 'DateTime', 'datePageModified', self.updated_at)
        return data

    @property
    def rawdata(self):
        return dict((k, self._get_raw_data_value(v)) for k, v in self.data.items())

    @classmethod
    def parse_schema_yaml(cls, body):
        data = {}

        # extract yaml
        m = re.search(cls.re_yaml_schema, body)
        if not m:
            return data

        # parse
        try:
            captured = m.group(1).replace('\t', '    ')
            parsed = yaml.load(captured)
        except ParserError as e:
            raise ValueError(e.message or u'invalid YAML format:<pre>%s</pre>' % m.group(0))

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
        try:
            data = self.data
        except ValueError:
            data = {}

        data = [
            (n, v, schema.humane_property(self.itemtype, n))
            for n, v in data.items()
            if (n not in ['schema', 'name', 'datePageModified']) and (not isinstance(v, schema.Property) or v.ptype != 'LongText')
        ]

        if len(data) == 0:
            return ''

        html = [
            u'<div class="structured-data">',
            u'<h1>Structured data</h1>',
            u'<dl>',
        ]

        data = sorted(data, key=operator.itemgetter(2))

        render_data_item = lambda itemname, itemvalue: u'<dd class="value value-%s"><span itemprop="%s">%s</span></dd>' % (itemname, itemname, itemvalue.render())
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
            for i, (rel, links) in enumerate(inlinks.items()):
                itemtype, rel = rel.split('/')
                lines.append(u'## %s <span class="hidden">(%s %d)</span>' % (schema.humane_property(itemtype, rel, True), itemtype, i))
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

        # other posts
        if older_title or newer_title:
            lines = [u'# Other Posts']
            if newer_title:
                lines.append(u'* {{.newer::newer}} [[%s]]\n{.noli}' % newer_title)
            if older_title:
                lines.append(u'* {{.older::older}} [[%s]]\n{.noli}' % older_title)
            body_parts.append(u'\n'.join(lines))

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
        #return cls.sanitize_html(rendered)

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
        return acl.ACL(default_acl, self.acl_read, self.acl_write).can_read(user, acl_r, acl_w)

    def can_write(self, user, default_acl=None, acl_r=None, acl_w=None):
        return acl.ACL(default_acl, self.acl_read, self.acl_write).can_write(user, acl_r, acl_w)

    def _get_raw_data_value(self, value):
        if type(value) == list:
            return [self._get_raw_data_value(v) for v in value]
        elif isinstance(value, schema.Property):
            return value.pvalue
        else:
            return value