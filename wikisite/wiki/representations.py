from django.template import RequestContext, loader
from models import WikiPage
import wiki_settings

class Representation(object):
    def __init__(self, content, content_type):
        self._content = content
        self._content_type = content_type

    def respond(self, httpres, head):
        self._respond(httpres, head, self._content_type, self._content)

    def _respond(self, httpres, head, content_type, content):
        httpres['Content-type'] = content_type
        if head:
            httpres['Content-length'] = str(len(content))
        else:
            httpres.write(content)
        return httpres


class EmptyRepresentation(Representation):
    def __init__(self, rescode):
        super(EmptyRepresentation, self).__init__(None, None)
        self._rescode = rescode

    def respond(self, httpres, head):
        httpres.status = 400


class TemplateRepresentation(Representation):
    def __init__(self, content, httpreq, template_path):
        if template_path.endswith('.html'):
            content_type = 'text/html; charset=utf-8'
        elif template_path.endswith('.xml'):
            content_type = 'text/xml; charset=utf-8'
        else:
            content_type = 'text/plain; charset=utf-8'

        super(TemplateRepresentation, self).__init__(content, content_type)
        self._httpreq = httpreq
        self._template_path = template_path

    def respond(self, httpres, head):
        html = template(self._httpreq, self._template_path, self._content)
        return self._respond(httpres, head, self._content_type, html)


def template(req, path, data):
    config = WikiPage.get_config()
    t = loader.get_template('wiki/%s' % path)
    c = RequestContext(req, data)
    c['config'] = config
    c['app'] = {'version': wiki_settings.VERSION}
    return t.render(c)