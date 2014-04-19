from django import template
from ..models import WikiPage, UserPreferences

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
    if user is None or user.is_anonymous():
        return '<span class="user" data-userpage="" data-email="">Anonymous</span>'

    preferences = UserPreferences.get_by_user(user)
    if preferences is None:
        return '<span class="user email" data-userpage="" data-email="">%s</span>' % user.email
    elif preferences.userpage_title is None or len(preferences.userpage_title.strip()) == 0:
        return '<span class="user email" data-userpage="" data-email="%s">%s</span>' % (user.email, user.email)
    path = to_abs_path(preferences.userpage_title)
    return '<a href="%s" class="user userpage wikilink" data-userpage="%s" data-email="%s">%s</a>' % (path, preferences.userpage_title, user.email, preferences.userpage_title)

@register.filter(name='to_rel_path')
def to_rel_path(title):
    return WikiPage.title_to_path(title)

@register.filter(name='to_abs_path')
def to_abs_path(title):
    return '/' + to_rel_path(title)

@register.filter(name='to_pluspath')
def to_pluspath(title):
    return '/%2B' + to_rel_path(title)