from django.http import HttpResponse
from resources import RedirectResource, PageResource, ChangeListResource, TitleIndexResource, TitleListResource, \
    UserPreferencesResource, PostListResource, SearchResultResource
from registration.backends.simple.views import RegistrationView
from registration.forms import RegistrationFormUniqueEmail
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
    elif request.method == 'POST':
        method = request.GET.get('_method', 'POST')
        if method == 'POST' and path == 'preferences':
            resource = UserPreferencesResource(request)
            return resource.post()