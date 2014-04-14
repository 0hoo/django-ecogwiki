# coding=utf-8
import json
import urllib2
from itertools import groupby
from models import WikiPage, UserPreferences
from django.http import HttpResponse, HttpResponseRedirect
from representations import Representation, TemplateRepresentation, EmptyRepresentation, JsonRepresentation, template
from .templatetags.wiki_extras import format_iso_datetime
from utils import title_grouper
import caching

def get_restype(req, default):
    return str(req.GET.get('_type', default))


class Resource(object):
    def __init__(self, req, default_restype='html', default_view='default'):
        self.req = req
        self.res = HttpResponse()
        self.default_restype = default_restype
        self.default_view = default_view

    def load(self):
        """Load data related to this resource"""
        return None

    def get(self, head):
        """Default implementation of GET"""
        representation = self.get_representation(self.load())
        return representation.respond(self.res, head)

    def get_representation(self, content):
        restype = get_restype(self.req, self.default_restype)
        view = self.req.GET.get('view', self.default_view)

        try:
            method = getattr(self, 'represent_%s_%s' % (restype, view))
        except:
            try:
                method = getattr(self, 'represent_%s_%s' % (self.default_restype, view))
            except:
                method = None

        if method is not None:
            return method(content)
        else:
            return EmptyRepresentation(400)


class RedirectResource(Resource):
    def __init__(self, req, location):
        super(RedirectResource, self).__init__(req)
        self._location = location
        if len(self.req.META['QUERY_STRING']):
            self._location += '?%s' % self.req.META['QUERY_STRING']
        self.res = HttpResponseRedirect(self._location)

    def get(self, head):
        self.res.status_code = 303
        return self.res


class PageLikeResource(Resource):
    def __init__(self, req, path):
        super(PageLikeResource, self).__init__(req)
        self.path = path

    def represent_html_default(self, page):
        if page.metadata['content-type'] != 'text/x-markdown':
            content = WikiPage.remove_metadata(page.body)
            content_type = '%s; charset=utf-8' % str(page.metadata['content-type'])
            return Representation(content, content_type)

        if page.metadata.get('redirect', None) is not None:
            return Representation(None, None)
        else:
            content = {
                'page': page,
                'message': self.res.get('X-Message', None),
            }
            if page.metadata.get('schema', None) == 'Blog':
                content['posts'] = page.get_posts(20)
            return TemplateRepresentation(content, self.req, 'wikipage.html')

    def represent_html_bodyonly(self, page):
        content = {
            'title': page.title,
            'body': page.rendered_body,
        }
        return TemplateRepresentation(content, self.req, 'generic_bodyonly.html')

    def represent_atom_default(self, page):
        content = render_atom(self.req, page.title, WikiPage.title_to_path(page.title),
                              page.get_posts(20), include_content=True, use_published_date=True)
        return Representation(content, 'text/xml; charset=utf-8')

    def represent_txt_default(self, page):
        return Representation(page.body, 'text/plain; charset=utf-8')

    def represent_json_default(self, page):
        content = {
            'title': page.title,
            'modifier': page.modifier.email() if page.modifier else None,
            'updated_at': format_iso_datetime(page.updated_at),
            'body': page.body,
            'revision': page.revision,
            'acl_read': page.acl_read,
            'acl_write': page.acl_write,
            'data': page.rawdata,
        }
        return JsonRepresentation(content)

    def _403(self, page, head=False):
        self.res.status_code = 403
        self.res['Content-Type'] = 'text/html; charset=utf-8'
        html = template(self.req, 'error.html', {
            'page': page,
            'description': 'You don\'t have a permission',
            'errors': [],
        })
        self.res.write(html)


class PageResource(PageLikeResource):
    def load(self):
        if self.req.user and not self.req.user.is_anonymous():
            caching.add_recent_email(self.req.user.email)
        page = WikiPage.get_by_path(self.path)
        page.set_cur_user(self.req.user)
        return page

    def get(self, head):
        page = self.load()

        if not page.can_read(self.req.user):
            self._403(page, head)
            return self.res

        if get_restype(self.req, 'html') == 'html' and self.req.GET.get('view', self.default_view) == 'default':
            redirect = page.metadata.get('redirect', None)
            if redirect is not None:
                self.res.location = '/' + WikiPage.title_to_path(redirect)
                self.res.status_code = 303
                return self.res

        representation = self.get_representation(page)
        return representation.respond(self.res, head)

    def put(self):
        page = self.load()

        revision = int(self.req.POST['revision'])
        new_body = self.req.POST['body']
        comment = self.req.POST.get('comment', '')
        preview = self.req.POST.get('preview', '0')
        partial = self.req.GET.get('partial', 'all')

        if preview == '1':
            pass

        try:
            page.update_content(new_body, revision, comment, self.req.user, partial=partial)
            self.res['X-Message'] = 'Successfully updated.'

            if partial == 'all':
                quoted_path = urllib2.quote(self.path.replace(' ', '_'))
                restype = get_restype(self.req, 'html')
                if restype == 'html':
                    self.res = HttpResponseRedirect(str('/' + quoted_path))
                else:
                    self.res = HttpResponseRedirect(str('/%s?_type=%s' % (quoted_path, restype)))
                self.res.status_code = 303
            else:
                self.res.status_code = 200
                self.res['Content-Type'] = 'application/json; charset=utf-8'
                self.res.write(json.dumps({'revision': page.revision}))

            return self.res
        except ValueError as e:
            print e

    def delete(self):
        page = self.load()
        try:
            page.delete()
            self.res.status_code = 204
        except RuntimeError as e:
            self.res.status_code = 403
        return self.res

    def represent_html_edit(self, page):
        if page.revision == 0 and self.req.GET.get('body'):
            page.body = self.req.GET.get('body')
        return TemplateRepresentation({'page': page}, self.req, 'wikipage.edit.html')


class ChangeListResource(Resource):
    def load(self):
        index = int(self.req.GET.get('index', '0'))
        count = min(50, int(self.req.GET.get('count', '50')))
        return {
            'cur_index': index,
            'next_index': index + 1,
            'count': count,
            'pages': WikiPage.get_changes(self.req.user, index, count),
        }

    def represent_html_default(self, data):
        return TemplateRepresentation(data, self.req, 'sp_changes.html')

    def represent_atom_default(self, data):
        content = render_atom(self.req, 'Changes', 'sp.changes', data['pages'])
        return Representation(content, 'text/xml; charset=utf-8')

    def represent_html_bodyonly(self, data):
        return TemplateRepresentation(data, self.req, 'sp_changes_bodyonly.html')


class TitleIndexResource(Resource):
    def load(self):
        return WikiPage.get_index(self.req.user)

    def represent_html_default(self, pages):
        page_group = groupby(pages, lambda p: title_grouper(p.title))
        page_group = [(grouper, list(values)) for grouper, values in page_group]
        return TemplateRepresentation({'page_group': page_group}, self.req, 'sp_index.html')

    def represent_atom_default(self, pages):
        content = render_atom(self.req, 'Title index', 'sp.index', pages)
        return Representation(content, 'text/xml; charset=utf-8')


class TitleListResource(Resource):
    def __init__(self, req):
        super(TitleListResource, self).__init__(req, default_restype='json')

    def load(self):
        return list(WikiPage.get_titles(self.req.user))

    def represent_json_default(self, titles):
        return JsonRepresentation(titles)


class UserPreferencesResource(Resource):
    def load(self):
        if (self.req.user is None) or (self.req.user.is_anonymous()):
            return None
        else:
            return UserPreferences.get_by_user(self.req.user)

    def get(self, head):
        if (self.req.user is None) or (self.req.user.is_anonymous()):
            self.res.status = 403
            return TemplateRepresentation({
                'page': {
                    'absolute_url': '/sp.preferences',
                    'title': 'User preferences',
                },
                'description': 'You don\'t have a permission',
                'errors': [],
            }, self.req, 'error.html').respond(self.res, head)
        else:
            representation = self.get_representation(self.load())
            return representation.respond(self.res, head)

    def post(self):
        if (self.req.user is None) or (self.req.user.is_anonymous()):
            self.res.status = 403
            return TemplateRepresentation({
                'page': {
                    'absolute_url': '/sp.preferences',
                    'title': 'User preferences',
                },
                'description': 'You don\'t have a permission',
                'errors': [],
            }, self.req, 'error.html').respond(self.res, False)

        prefs = self.load()
        prefs.userpage_title = self.req.POST['userpage_title']
        prefs.save()

        self.res['X-Message'] = 'Successfully updated.'
        representation = self.get_representation(prefs)
        return representation.respond(self.res, False)

    def represent_html_default(self, prefs):
        return TemplateRepresentation({
            'preferences': prefs,
            'message': self.res.get('X-Message', None),
        }, self.req, 'sp_preferences.html')