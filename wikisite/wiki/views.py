from resources import RedirectResource, PageResource
from registration.backends.simple.views import RegistrationView
from registration.forms import RegistrationFormUniqueEmail


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