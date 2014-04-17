from django.http import HttpResponse
from resources import RedirectResource, PageResource, ChangeListResource, TitleIndexResource, TitleListResource, \
    UserPreferencesResource, PostListResource, SearchResultResource, RevisionListResource, RevisionResource, \
    RelatedPagesResource, WikiqueryResource
from representations import TemplateRepresentation
from registration.backends.simple.views import RegistrationView
from registration.forms import RegistrationFormUniqueEmail
from models import WikiPage
import caching


class WikiRegistrationView(RegistrationView):
    form_class = RegistrationFormUniqueEmail

    def get_success_url(self, request, user):
        return '/'


def index(request, path, head=False):
    if request.method == 'GET':
        if path == '':
            resource = RedirectResource(request, '/Home')
            return resource.get(head)
        elif request.path.find(' ') != -1:
            resource = RedirectResource(request, '/%s' % WikiPage.title_to_path(path))
            return resource.get(head)
        elif request.GET.get('rev') == 'list':
            resource = RevisionListResource(request, path)
            return resource.get(head)
        elif request.GET.get('rev', '') != '':
            resource = RevisionResource(request, path, request.GET.get('rev', ''))
            return resource.get(head)
        else:
            resource = PageResource(request, path)
            return resource.get(head)
    elif request.method == 'POST':
        method = request.GET.get('_method', 'POST')
        if method == 'DELETE':
            resource = PageResource(request, path)
            return resource.delete()
        elif method == 'PUT':
            resource = PageResource(request, path)
            return resource.put()
        else:
            resource = PageResource(request, path)
            return resource.post()
    elif request.method == 'PUT':
        resource = PageResource(request, path)
        return resource.put()
    elif request.method == 'DELETE':
        pass


def special(request, path):
    head = False
    if request.method == 'GET':
        if path == u'changes':
            resource = ChangeListResource(request)
            return resource.get(head)
        elif path == u'index':
            resource = TitleIndexResource(request)
            return resource.get(head)
        elif path == u'posts':
            resource = PostListResource(request)
            return resource.get(head)
        elif path == u'titles':
            resource = TitleListResource(request)
            return resource.get(head)
        elif path == u'search':
            resource = SearchResultResource(request)
            return resource.get(head)
        elif path == u'flush_cache':
            caching.flush_all()
            response = HttpResponse()
            response['Content-Type'] = 'text/plain; charset=utf-8'
            response.write('Done!')
            return response
        elif path == u'preferences':
            resource = UserPreferencesResource(request)
            return resource.get(head)
        elif path == u'opensearch':
            representation = TemplateRepresentation({}, request, 'opensearch.xml')
            return representation.respond(HttpResponse(), head)
        elif path == u'randomly_update_related_pages':
            recent = request.GET.get('recent', '0')
            titles = WikiPage.randomly_update_related_links(50, recent == '1')
            response = HttpResponse()
            response['Content-Type'] = 'text/plain; charset=utf-8'
            response.write('\n'.join(titles))
            return response
    elif request.method == 'POST':
        method = request.GET.get('_method', 'POST')
        if method == 'POST' and path == 'preferences':
            resource = UserPreferencesResource(request)
            return resource.post()


def related(request, path):
    head = False
    resource = RelatedPagesResource(request, path)
    return resource.get(head)


def wikiquery(request, path):
    head = False
    resource = WikiqueryResource(request, path)
    return resource.get(head)
