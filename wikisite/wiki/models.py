import re
import random
import operator
from datetime import datetime
from collections import OrderedDict
import yaml

from django.utils.timezone import utc
from django.db import models
from django.contrib.auth.models import User
from jsonfield import JSONField

from lib.bzrlib.merge3 import Merge3
from markdownext import md_wikilink
from page_operation_mixin import PageOperationMixin, md
from utils import merge_dicts
import schema
import caching
from toc_generator import TocGenerator
import wiki_settings
import search


class ConflictError(ValueError):
    def __init__(self, message, base, provided, merged):
        Exception.__init__(self, message)
        self.base = base
        self.provided = provided
        self.merged = merged


class UserPreferences(models.Model):
    user = models.ForeignKey(User)
    userpage_title = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    @classmethod
    def savePrefs(cls, user, userpage_title):
        prefs = cls.get_by_user(user)
        prefs.userpage_title = userpage_title
        prefs.save()
        return prefs

    @classmethod
    def get_by_user(cls, user):
        prefs = UserPreferences.objects.filter(user__email=user.email)
        if not prefs:
            prefs = UserPreferences()
            prefs.user = user
            prefs.created_at = datetime.utcnow().replace(tzinfo=utc)
            return prefs
        return prefs[0]


class SchemaDataIndexManager(models.Manager):
    def has_match(self, title, name, value):
        return len(self.filter(title=title, name=name, value=value)) > 0

    def indexes(self, title, name, v):
        return self.filter(title=title, name=name, value=(v.pvalue if isinstance(v, schema.Property) else v))


class SchemaDataIndex(models.Model):
    title = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    objects = SchemaDataIndexManager()

    def __str__(self):
        return self.title + ' : ' + self.name + ' : ' + self.value

    @classmethod
    def rebuild_index(cls, title, data):
        # delete
        SchemaDataIndex.objects.filter(title=title).delete()

        # insert
        entities = [cls(title=title, name=name, value=v.pvalue if isinstance(v, schema.Property) else v)
                    for name, v in cls.data_as_pairs(data)]
        for e in entities:
            e.save()

    @classmethod
    def update_index(cls, title, old_data, new_data):
        old_pairs = cls.data_as_pairs(old_data)
        new_pairs = cls.data_as_pairs(new_data)

        deletes = old_pairs.difference(new_pairs)
        inserts = new_pairs.difference(old_pairs)

        # delete
        for name, v in deletes:
            indexes = SchemaDataIndex.objects.indexes(title, name, v)
            for i in indexes:
                i.delete()

        # insert
        for name, v in inserts:
            i = SchemaDataIndex(title=title, name=name, value=(v.pvalue if isinstance(v, schema.Property) else v))
            i.save()

    @staticmethod
    def data_as_pairs(data):
        pairs = set()
        for key, value in data.items():
            if type(value) == list:
                pairs.update((key, v) for v in value)
            else:
                pairs.add((key, value))
        return pairs

    @classmethod
    def query_by_title(cls, title):
        return SchemaDataIndex.objects.filter(title=title)

    @classmethod
    def query_titles(cls, name, value):
        return [i.title for i in SchemaDataIndex.objects.filter(name=name, value=value)]

    @classmethod
    def has_match(cls, title, name, value):
        return SchemaDataIndex.objects.filter(title=title, name=name, value=value).count() > 0


class WikiPage(models.Model, PageOperationMixin):
    re_normalize_title = re.compile(ur'([\[\]\(\)\~\!\@\#\$\%\^\&\*\-'
                                    ur'\=\+\\:\;\'\"\,\.\?\<\>\s]|'
                                    ur'\bthe\b|\ban?\b)')

    itemtype_path = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    body = models.TextField()
    description = models.CharField(max_length=255)
    comment = models.CharField(max_length=999)
    modifier = models.ForeignKey(User, null=True, blank=True)
    acl_read = models.CharField(max_length=255)
    acl_write = models.CharField(max_length=255)
    revision = models.IntegerField()
    updated_at = models.DateTimeField(null=True)

    published_at = models.DateTimeField(null=True)
    published_to = models.CharField(max_length=255, null=True)
    older_title = models.CharField(max_length=255, null=True)
    newer_title = models.CharField(max_length=255, null=True)

    _inlinks = JSONField()
    _outlinks = JSONField()
    _related_links = JSONField()

    def __str__(self):
        return self.title

    def get_posts(self, index=0, count=50):
        return WikiPage.get_posts_of(self.title, index, count)

    @classmethod
    def search(cls, expression):
        # parse
        parsed = search.parse_expression(expression)

        # evaluate
        pos, neg = parsed['pos'], parsed['neg']
        pos_pages = [cls.get_by_title(t, True) for t in pos]
        neg_pages = [cls.get_by_title(t, True) for t in neg]
        scoretable = search.evaluate(
            dict((page.title, page.link_scoretable) for page in pos_pages),
            dict((page.title, page.link_scoretable) for page in neg_pages)
        )

        return scoretable

    @classmethod
    def wikiquery(cls, q, user=None):
        email = user.email if (user is not None and not user.is_anonymous()) else 'None'
        results = caching.get_wikiquery(q, email)
        if results is None:
            page_query, attrs = search.parse_wikiquery(q)
            titles = cls._evaluate_pages(page_query)
            accessible_titles = WikiPage.get_titles(user).intersection(titles)

            results = []
            if attrs == [u'name']:
                results += [{u'name': title} for title in accessible_titles]
            else:
                for title in accessible_titles:
                    pagedata = WikiPage.get_by_title(title, follow_redirect=True).data
                    results.append(OrderedDict((attr, pagedata[attr] if attr in pagedata else None) for attr in attrs))

            if len(results) == 1:
                results = results[0]

            caching.set_wikiquery(q, email, results)
        return results

    @classmethod
    def _evaluate_pages(cls, q):
        if len(q) == 1:
            pages = cls._evaluate_pages(q[0])
        elif len(q) == 2:
            pages = cls._evaluate_page_query_term(q[0], q[1])
        else:
            pages = cls._evaluate_page_query_expr(q[0], q[1], q[2:])
        return pages

    @classmethod
    def _evaluate_page_query_term(cls, name, value):
        if name == 'schema' and value.find('/') == -1:
            value = schema.get_itemtype_path(value)
        return SchemaDataIndex.query_titles(name, value)

    @classmethod
    def _evaluate_page_query_expr(cls, operand, op, rest):
        pages1 = cls._evaluate_pages(operand)
        pages2 = cls._evaluate_pages(rest)

        if op == '*':
            return set(pages1).intersection(pages2)
        elif op == '+':
            return set(pages1).union(pages2)
        raise ValueError('Invalid operator: %s' % op)

    @classmethod
    def get_index(cls, user=None):
        pages = WikiPage.objects.all().order_by('title')
        default_permission = WikiPage.get_default_permission()
        return [page for page in pages
                if page.updated_at and page.can_read(user, default_permission)]

    @classmethod
    def get_titles(cls, user=None):
        email = user.email if (user is not None and not user.is_anonymous) else u'None'
        titles = caching.get_titles(email)
        if titles is None:
            titles = {page.title for page in cls.get_index(user)}
            caching.set_titles(email, titles)

        return titles

    @classmethod
    def get_changes(cls, user, index=0, count=50):
        offset = index * count
        pages = WikiPage.objects.filter(updated_at__isnull=False).order_by('-updated_at')[offset:offset+count]
        default_permission = WikiPage.get_default_permission()
        return [page for page in pages if page.can_read(user, default_permission)]

    @classmethod
    def get_posts_of(cls, title, index=0, count=50):
        offset = index * count
        pages = WikiPage.objects.filter(published_to=title, published_at__isnull=False).order_by('-published_at')[offset:offset+count]
        return pages

    @classmethod
    def randomly_update_related_links(cls,  iteration, recent=False):
        if recent:
            titles = [p.title for p in WikiPage.get_changes(None, count=iteration)]
        else:
            titles = WikiPage.get_titles()

        if len(titles) > iteration:
            titles = random.sample(titles, iteration)

        pages = [cls.get_by_title(title, follow_redirect=True) for title in titles]
        for p in pages:
            if p.update_related_links():
                p.save()

        return titles

    @classmethod
    def get_config(cls):
        result = caching.get_config()
        if result is None:
            result = wiki_settings.DEFAULT_CONFIG

            try:
                config_page = cls.get_by_title('.config')
                user_config = yaml.load(PageOperationMixin.remove_metadata(config_page.body))
            except:
                user_config = None
            user_config = user_config or {}

            def merge_dict(target_dict, source_dict):
                for (key, value) in source_dict.iteritems():
                    if type(value) != dict:
                        target_dict[key] = value
                    else:
                        merge_dict(target_dict.setdefault(key, {}), value)

            merge_dict(result, user_config)

            caching.set_config(result)
        return result

    @property
    def hashbangs(self):
        value = caching.get_hashbangs(self.title)
        if value is None:
            value = super(WikiPage, self).hashbangs
            caching.set_hashbangs(self.title, value)
        return value

    def get_inlinks(self):
        if not self._inlinks:
            self._inlinks = {}
        return self._inlinks

    def set_inlinks(self, value):
        self._inlinks = value
    inlinks = property(get_inlinks, set_inlinks)

    def get_outlinks(self):
        if not self._outlinks:
            self._outlinks = {}
        return self._outlinks

    def set_outlinks(self, value):
        self._outlinks = value
    outlinks = property(get_outlinks, set_outlinks)

    def get_related_links(self):
        if not self._related_links:
            self._related_links = {}
        return self._related_links

    def set_related_links(self, value):
        self._related_links = value
    related_links = property(get_related_links, set_related_links)

    @property
    def is_old_revision(self):
        return False

    @classmethod
    def get_by_path(cls, path, follow_redirect=False):
        return cls.get_by_title(cls.path_to_title(path), follow_redirect)

    @classmethod
    def get_by_title(cls, title, follow_redirect=False):
        if title is None:
            return None

        if title[0] == u'=':
            raise ValueError(u'WikiPage title cannot starts with "="')

        try:
            page = WikiPage.objects.get(title=title)
        except WikiPage.DoesNotExist:
            page = None

        if page is None:
            page = WikiPage(title=title, body=u'', revision=0)
        elif follow_redirect:
            page = cls._follow_redirect(page)

        return page

    @classmethod
    def get_default_permission(cls):
        return {
            'read': ['all'],
            'write': ['login'],
        }

    @property
    def user_can_write(self):
        if self.cur_user and self.cur_user.is_anonymous():
            return self.can_write(None)
        else:
            return self.can_write(self.cur_user)

    def can_write(self, user, default_acl=None, acl_r=None, acl_w=None):
        if user and user.is_anonymous():
            user = None
        if default_acl is None:
            default_acl = WikiPage.get_default_permission()
        return super(WikiPage, self).can_write(user, default_acl, acl_r, acl_w)

    def can_read(self, user, default_acl=None, acl_r=None, acl_w=None):
        if user and user.is_anonymous():
            user = None
        if default_acl is None:
            default_acl = WikiPage.get_default_permission()
        return super(WikiPage, self).can_read(user, default_acl, acl_r, acl_w)

    def delete(self, user=None):
        if not user or user.is_anonymous() or not user.is_superuser:
            raise RuntimeError('Only admin can delete pages.')

        self.update_content('', self.revision, user=user, dont_create_rev=True)
        self._update_inlinks({}, {'relatedTo': [p[0] for p in self.paths[:-1]]})
        self.related_links = {}
        self.modifier = None
        self.updated_at = None
        self.revision = 0
        self.save()

        for r in self.revisions.all():
            r.delete()

        caching.del_titles()

    @property
    def rendered_body(self):
        value = caching.get_rendered_body(self.title)
        if value is None:
            value = super(WikiPage, self).rendered_body
            caching.set_rendered_body(self.title, value)
        return value

    @property
    def data(self):
        value = caching.get_data(self.title)
        if value is None:
            value = super(WikiPage, self).data
            caching.set_data(self.title, value)
        return value

    @property
    def metadata(self):
        value = caching.get_metadata(self.title)
        if value is None:
            value = super(WikiPage, self).metadata
            caching.set_metadata(self.title, value)
        return value

    @property
    def hashbangs(self):
        value = caching.get_hashbangs(self.title)
        if value is None:
            value = super(WikiPage, self).hashbangs
            caching.set_hashbangs(self.title, value)
        return value

    def update_content(self, content, base_revision, comment='', user=None, force_update=False, dont_create_rev=False,
                       partial='all'):
        if partial == 'all':
            return self._update_content_all(content, base_revision, comment, user, force_update, dont_create_rev)
        else:
            raise ValueError('Invalid partial expression: %s' % partial)

    def _update_content_all(self, body, base_revision, comment, user, force_update, dont_create_rev):
        # do not update if the body is not changed
        if not force_update and self.body == body:
            return False

        # validate and prepare new contents
        new_data, new_md = self.validate_new_content(base_revision, body, user)
        new_body = self._merge_if_needed(base_revision, body)

        # get old data and metadata
        old_md = self.metadata.copy()
        old_data = self.data.copy()

        # delete caches
        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        caching.del_metadata(self.title)
        caching.del_data(self.title)

        # update model and save
        self.body = new_body
        if user and not user.is_anonymous():
            self.modifier = user
        self.description = PageOperationMixin.make_description(new_body)
        self.acl_read = new_md.get('read', '')
        self.acl_write = new_md.get('write', '')
        self.comment = comment
        self.itemtype_path = schema.get_itemtype_path(new_md['schema'])
        self._update_pub_state(new_md, old_md)
        if not dont_create_rev:
            self.revision += 1
        if not force_update:
            self.updated_at = datetime.utcnow().replace(tzinfo=utc)
        self.save()

        # create revision
        if not dont_create_rev:
            rev = WikiPageRevision(page=self, title=self.title, body=self.body,
                                   created_at=self.updated_at, revision=self.revision,
                                   comment=self.comment, modifier=self.modifier)
            rev.save()

        self.update_links_and_data(old_md.get('redirect'), new_md.get('redirect'), old_data, new_data)

        # delete config cache
        #if self.title == '.config':
        #    caching.del_config()

        # delete title cache if it's a new page
        if self.revision == 1:
            caching.del_titles()

        return True

    def _merge_if_needed(self, base_revision, new_body):
        if self.revision == base_revision:
            return new_body

        base = WikiPageRevision.objects.get(title=self.title, revision=base_revision).body
        merged = ''.join(Merge3(base, self.body, new_body).merge_lines())
        conflicted = len(re.findall(PageOperationMixin.re_conflicted, merged)) > 0
        if conflicted:
            raise ConflictError('Conflicted', base, new_body, merged)
        return merged

    def update_links_and_data(self, old_redir, new_redir, old_data, new_data):
        self.update_links(old_redir, new_redir)
        SchemaDataIndex.update_index(self.title, old_data, new_data)

    def update_links(self, old_redir, new_redir):
        """Updates outlinks of this page and inlinks of target pages"""
        # 1. process "redirect" metadata
        self._update_redirected_links(new_redir, old_redir)

        # 2. update inlinks
        cur_outlinks = self.outlinks
        new_outlinks = {}
        for rel, titles in self._parse_outlinks().items():
            new_outlinks[rel] = list({WikiPage.get_by_title(t, follow_redirect=True).title for t in titles})
        if self.acl_read:
            # delete all inlinks of target pages if the source page has a read restriction
            added_outlinks = {}
            removed_outlinks = cur_outlinks
        else:
            added_outlinks = {}
            for rel, titles in new_outlinks.items():
                added_outlinks[rel] = titles
                if rel in cur_outlinks:
                    added_outlinks[rel] = set(added_outlinks[rel]).difference(cur_outlinks[rel])
            removed_outlinks = {}
            for rel, titles in cur_outlinks.items():
                removed_outlinks[rel] = titles
                if rel in new_outlinks:
                    removed_outlinks[rel] = set(removed_outlinks[rel]).difference(new_outlinks[rel])

        self._update_inlinks(added_outlinks, removed_outlinks)

        [new_outlinks[rel].sort() for rel in new_outlinks.keys()]
        self.outlinks = new_outlinks
        self.save()

    def _update_inlinks(self, added_outlinks, removed_outlinks):
        # handle added links
        updates = []
        for rel, titles in added_outlinks.items():
            for title in titles:
                page = WikiPage.get_by_title(title, follow_redirect=True)
                page.add_inlink(self.title, rel)
                page.save()
                updates.append(page)

        if updates:
            for page in updates:
                caching.del_rendered_body(page.title)
                caching.del_hashbangs(page.title)

        # handle removed links
        updates = []
        deletes = []
        for rel, titles in removed_outlinks.items():
            for title in titles:
                page = WikiPage.get_by_title(title, follow_redirect=True)
                page.del_inlink(self.title, rel)
                if len(page.inlinks) == 0 and page.revision == 0 and page.id:
                    deletes.append(page)
                else:
                    updates.append(page)

        for page in updates + deletes:
            caching.del_rendered_body(page.title)
            caching.del_hashbangs(page.title)

        for page in updates:
            page.save()

        for page in deletes:
            page.set_cur_user(self.cur_user)
            page.delete(self.cur_user)

    def _update_redirected_links(self, new_redir, old_redir):
        """Change in/out links of self and related pages according to new redirect metadata"""
        if old_redir == new_redir:
            return

        source = WikiPage.get_by_title(old_redir, follow_redirect=True) if old_redir else self
        if len(source.inlinks) == 0:
            return
        target = WikiPage.get_by_title(new_redir, follow_redirect=True) if new_redir else self

        updates = [source, target]
        for rel, titles in source.inlinks.items():
            for t in titles:
                page = WikiPage.get_by_title(t)
                page.del_outlink(source.title, rel)
                page.add_outlink(target.title, rel)
                updates.append(page)
            target.add_inlinks(source.inlinks[rel], rel)
            del source.inlinks[rel]

        for p in updates:
            p.save()

        for page in updates:
            caching.del_rendered_body(page.title)
            caching.del_hashbangs(page.title)

    def get_similar_titles(self, user):
        return WikiPage.similar_titles(WikiPage.get_titles(user), self.title)

    @classmethod
    def similar_titles(cls, titles, target):
        normalized_target = cls.normalize_title(target)
        if len(normalized_target) == 0:
            return OrderedDict([
                (u'startswiths', []),
                (u'endswiths', []),
                (u'contains', []),
            ])

        contains = []
        startswiths = []
        endswiths = []
        for title in titles:
            if title == target:
                continue

            normalized_title = cls.normalize_title(title)

            if normalized_title.find(normalized_target) == -1:
                pass
            elif normalized_title.startswith(normalized_target):
                startswiths.append(title)
            elif normalized_title.endswith(normalized_target):
                endswiths.append(title)
            else:
                contains.append(title)

        return OrderedDict([
            (u'startswiths', startswiths),
            (u'endswiths', endswiths),
            (u'contains', contains),
        ])

    @classmethod
    def normalize_title(cls, title):
        return re.sub(cls.re_normalize_title, u'', title.lower())

    def update_related_links(self, max_distance=5):
        """Update related_links score table by random walk"""
        if len(self.outlinks) == 0:
            return False

        # random walk
        score_table = self.related_links
        updated = WikiPage._update_related_links(self, self, 0.1, score_table, max_distance)
        if not updated:
            return False

        self.related_links = score_table
        self.normalize_related_links()
        return True

    def normalize_related_links(self):
        related_links = self.related_links

        # filter out obvious(direct) links
        outlinks = reduce(lambda x, y: x + y, self.outlinks.values(), [])
        inlinks = reduce(lambda x, y: x + y, self.inlinks.values(), [])
        direct_links = set(outlinks + inlinks)
        related_links = dict(filter(lambda (k, v): k not in direct_links, related_links.items()))

        # filter out insignificant links
        if len(related_links) > 30:
            sorted_tuples = sorted(related_links.iteritems(),
                                   key=operator.itemgetter(1))
            related_links = OrderedDict(sorted_tuples[-30:])

        # normalize score
        total = sum(related_links.values())
        if total > 1.0:
            for link, score in related_links.items():
                related_links[link] = score / total

        # done
        self.related_links = related_links

    @classmethod
    def _update_related_links(cls, start_page, page, score, score_table, distance):
        if distance == 0:
            return False

        #if l != start_page.title
        nested_links = [l for l in page.outlinks.values()]
        links = reduce(lambda a, b: a + b, nested_links, [])
        links = [l for l in links if l != start_page.title]
        if len(links) == 0:
            return False

        next_page = WikiPage.get_by_title(random.choice(links), follow_redirect=True)
        next_link = next_page.title
        if next_link not in score_table:
            score_table[next_link] = 0.0

        next_score = score * 0.5
        score_table[next_link] = next_score

        # update target page's relate links
        if next_page.revision > 0:
            if start_page.title not in next_page.related_links:
                next_page.related_links[start_page.title] = 0.0

            next_page_score = next_score
            next_page.related_links[start_page.title] += next_page_score
            next_page.normalize_related_links()
            next_page.save()

        cls._update_related_links(start_page, next_page, next_score, score_table, distance - 1)
        return True

    def validate_new_content(self, base_revision, new_body, user):
        # check metadata
        new_md = PageOperationMixin.parse_metadata(new_body)

        ## prevent self-revoke
        acl_r = new_md.get('read', '')
        acl_r = acl_r.split(',') if acl_r else []
        acl_w = new_md.get('write', '')
        acl_w = acl_w.split(',') if acl_w else []

        if not self.can_read(user, acl_r=acl_r, acl_w=acl_w):
            raise ValueError('Cannot restrict your permission')
        if not self.can_write(user, acl_r=acl_r, acl_w=acl_w):
            raise ValueError('Cannot restrict your permission')

        # prevent circular-redirection
        try:
            WikiPage._follow_redirect(self, new_md.get(u'redirect'))
        except ValueError as e:
            raise e

        # check data
        new_data = PageOperationMixin.parse_data(self.title, new_body, new_md['schema'])
        if any(type(value) == schema.InvalidProperty for value in new_data.values()):
            raise ValueError('Invalid schema data')

        # check revision
        if self.revision < base_revision:
            raise ValueError('Invalid revision number: %d' % base_revision)

        # check headings
        if not TocGenerator(md.convert(new_body)).validate():
            raise ValueError("Duplicate paths not allowed")

        return new_data, new_md

    def _update_pub_state(self, new_md, old_md):
        pub_old = u'pub' in old_md
        pub_new = u'pub' in new_md
        pub_old_title = old_md['pub'] if pub_old else None
        pub_new_title = new_md['pub'] if pub_new else None
        if pub_old and pub_new and (pub_old_title != pub_new_title):
            # if target page is changed
            self._unpublish(save=False)
            self._publish(title=pub_new_title, save=False)
        else:
            if pub_new:
                self._publish(title=pub_new_title, save=False)
            else:
                self._unpublish(save=False)

    def _publish(self, title, save):
        if self.published_at is not None and self.published_to == title:
            return

        posts = WikiPage.get_posts_of(title, index=0, count=1)

        if len(posts) > 0:
            latest = posts[0]
            latest.newer_title = self.title
            latest.save()
            self.older_title = latest.title

        self.published_to = title
        self.published_at = datetime.utcnow().replace(tzinfo=utc)

        if save:
            self.save()

        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        if self.newer_title:
            caching.del_rendered_body(self.newer_title)
            caching.del_hashbangs(self.newer_title)
        if self.older_title:
            caching.del_rendered_body(self.older_title)
            caching.del_hashbangs(self.older_title)

    def _unpublish(self, save):
        if self.published_at is None:
            return

        caching.del_rendered_body(self.title)
        caching.del_hashbangs(self.title)
        if self.newer_title:
            caching.del_rendered_body(self.newer_title)
            caching.del_hashbangs(self.newer_title)
        if self.older_title:
            caching.del_rendered_body(self.older_title)
            caching.del_hashbangs(self.older_title)

        older = WikiPage.get_by_title(self.older_title)
        newer = WikiPage.get_by_title(self.newer_title)

        if self.older_title is not None and self.newer_title is not None:
            newer.older_title = self.older_title
            older.newer_title = self.newer_title
            newer.save()
            older.save()
        elif self.older_title is not None:
            older.newer_title = None
            older.save()
        elif self.newer_title is not None:
            newer.older_title = None
            newer.save()

        self.published_at = None
        self.published_to = None
        self.older_title = None
        self.newer_title = None

        if save:
            self.save()

    def _schema_item_to_links(self, name, value):
        if isinstance(value, schema.Property) and value.is_wikilink():
            return md_wikilink.parse_wikilinks(self.itemtype, u'[[%s::%s]]' % (name, value.pvalue))
        elif type(value) == str or type(value) == unicode:
            return md_wikilink.parse_wikilinks(self.itemtype, u'[[%s::%s]]' % (name, value))
        return {}

    def _parse_outlinks(self):
        # links in hierarchical title and body
        dicts = [
            {'%s/relatedTo' % self.itemtype: [path[0] for path in self.paths[:-1]]},
            md_wikilink.parse_wikilinks(self.itemtype, WikiPage.remove_metadata(self.body)),
        ]

        # links in structured data
        for name, value in self.data.items():
            if type(value) is list:
                dicts += [self._schema_item_to_links(name, v) for v in value]
            else:
                dicts.append(self._schema_item_to_links(name, value))

        # merge
        merged = merge_dicts(dicts, force_list=True)

        # exclude links to this page
        return dict((k, v) for k, v in merged.items()
                    if not((type(v) == list and self.title in v) or self.title == v))

    def add_inlinks(self, titles, rel):
        WikiPage._add_inout_links(self.inlinks, titles, rel)

    def add_outlinks(self, titles, rel):
        WikiPage._add_inout_links(self.outlinks, titles, rel)

    def add_inlink(self, title, rel):
        WikiPage._add_inout_link(self.inlinks, title, rel)

    def add_outlink(self, title, rel):
        WikiPage._add_inout_link(self.outlinks, title, rel)

    def del_inlink(self, title, rel=None):
        WikiPage._del_inout_link(self.inlinks, title, rel)

    def del_outlink(self, title, rel=None):
        WikiPage._del_inout_link(self.outlinks, title, rel)

    @staticmethod
    def _add_inout_links(links, titles, rel):
        if len(titles) == 0:
            return
        if rel not in links:
            links[rel] = []
        links[rel] += titles
        links[rel].sort()

    @staticmethod
    def _add_inout_link(links, title, rel):
        WikiPage._add_inout_links(links, [title], rel)

    @staticmethod
    def _del_inout_link(links, title, rel=None):
        if rel in links:
            try:
                links[rel].remove(title)
            except ValueError:
                pass
            except KeyError:
                pass

            if len(links[rel]) == 0:
                del links[rel]
        else:
            for rel, titles in links.items():
                try:
                    titles.remove(title)
                except ValueError:
                    pass

                if len(titles) == 0:
                    del links[rel]

    @classmethod
    def _follow_redirect(cls, page, new_redir=None):
        trail = {page.title}

        while new_redir or ('redirect' in page.metadata):
            next_title = new_redir or page.metadata['redirect']

            # set it None to make it work just one time
            new_redir = None

            if next_title in trail:
                raise ValueError('Circular redirection detected')
            page = cls.get_by_title(next_title)
        return page

    @property
    def get_similar_title_items(self):
        return self.get_similar_titles(self.cur_user).items()

    @property
    def link_scoretable(self):
        """Returns all links ordered by score"""

        # related links
        related_links_scoretable = self.related_links

        # in/out links
        inlinks = reduce(lambda a, b: a + b, self.inlinks.values(), [])
        outlinks = reduce(lambda a, b: a + b, self.outlinks.values(), [])
        inout_links = set(inlinks + outlinks).difference(related_links_scoretable.keys())
        inout_links_len = len(inout_links)
        inout_score = 1.0 / inout_links_len if inout_links_len != 0 else 0.0
        inout_links_scoretable = dict(zip(inout_links, [inout_score] * inout_links_len))

        scoretable = dict(inout_links_scoretable.items() + related_links_scoretable.items())
        sorted_scoretable = sorted(scoretable.iteritems(),
                                   key=operator.itemgetter(1),
                                   reverse=True)
        return OrderedDict(sorted_scoretable)

    @property
    def hashbangs(self):
        value = caching.get_hashbangs(self.title)
        if value is None:
            value = super(WikiPage, self).hashbangs
            caching.set_hashbangs(self.title, value)
        return value


class WikiPageRevision(models.Model, PageOperationMixin):
    title = models.CharField(max_length=255)
    body = models.TextField()
    revision = models.IntegerField()
    comment = models.CharField(max_length=999)
    page = models.ForeignKey(WikiPage, related_name='revisions')
    modifier = models.ForeignKey(User, null=True, blank=True)
    acl_read = models.CharField(max_length=255)
    acl_write = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    def __str__(self):
        return self.title + ' : ' + str(self.revision)

    @property
    def absolute_url(self):
        return u'/%s?rev=%d' % (PageOperationMixin.title_to_path(self.title), int(self.revision))

    @property
    def is_old_revision(self):
        return True

    @property
    def updated_at(self):
        return self.created_at

    @property
    def inlinks(self):
        return {}

    @property
    def outlinks(self):
        return {}

    @property
    def related_links(self):
        return {}

    @property
    def older_title(self):
        return None

    @property
    def newer_title(self):
        return None