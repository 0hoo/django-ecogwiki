from django import template
from ..models import WikiPage

register = template.Library()


def _format_datetime(value, pattern):
    return '' if value is None else value.strftime(pattern)

@register.filter(name='isodt')
def format_iso_datetime(v):
    return _format_datetime(v, '%Y-%m-%dT%H:%M:%SZ')

@register.filter(name='dt')
def format_datetime(v):
    return _format_datetime(v, '%Y-%m-%d %H:%M:%S')

@register.filter(name='sdt')
def format_short_datetime(v):
    return _format_datetime(v, '%m-%d %H:%M')

@register.filter(name='userpage', is_safe=True)
def userpage_link(user):
    return '<span class="user">Anonymous</span>'

@register.filter(name='to_rel_path')
def to_rel_path(title):
    return WikiPage.title_to_path(title)

@register.filter(name='to_abs_path')
def to_abs_path(title):
    return '/' + to_rel_path(title)

@register.filter(name='to_pluspath')
def to_pluspath(title):
    return '/%2B' + to_rel_path(title)

# @register.filter(name='has_supported_language')
# def has_supported_language(hashbangs):
#     langs = WikiPage.get_config()['highlight']['supported_languages']
#     return any(lang in langs for lang in hashbangs)