import urllib
from django.core.cache import cache

max_recent_users = 20


def add_recent_email(email):
    emails = get_recent_emails()
    if len(emails) > 0 and emails[-1] == email:
        return
    if email in emails:
        emails.remove(email)
    emails.append(email)
    value = emails[-max_recent_users:]
    _set_cache('view:recentemails', value)


def get_recent_emails():
    key = 'view:recentemails'
    try:
        emails = cache.get(key)
        if emails is None:
            cache.clear()
            emails = []
        return emails
    except:
        return []

def _set_cache(key, value):
    cache.set(key, value)


def get_schema_set():
    return cache.get('schema_set')


def set_schema_set(value):
    _set_cache('schema_set', value)


def get_schema(key):
    return cache.get('schema:%s' % key)


def set_schema(key, value):
    _set_cache('schema:%s' % key, value)


def get_schema_itemtypes():
    return cache.get('schema:itemtypes')


def set_schema_itemtypes(value):
    _set_cache('schema:itemtypes', value)


def get_schema_datatype(type_name):
    return cache.get('schema:datatype:%s' % urllib.quote(type_name))


def set_schema_datatype(type_name, prop):
    _set_cache('schema:datatype:%s' % urllib.quote(type_name), prop)


def get_schema_property(prop_name):
    return cache.get('schema:prop:%s' % urllib.quote(prop_name))


def set_schema_property(prop_name, prop):
    _set_cache('schema:prop:%s' % urllib.quote(prop_name), prop)


def get_hashbangs(title):
    cache.get('model:hashbangs:%s' % urllib.quote(title))


def set_hashbangs(title, value):
    _set_cache('model:hashbangs:%s' % urllib.quote(title), value)


def get_rendered_body(title):
    return cache.get('model:rendered_body:%s' % urllib.quote(title))


def set_rendered_body(title, value):
    if not value:
        return
    _set_cache('model:rendered_body:%s' % urllib.quote(title), value)


def get_data(title):
    return cache.get('model:data:%s' % urllib.quote(title))


def set_data(title, value):
    _set_cache('model:data:%s' % urllib.quote(title), value)


def get_metadata(title):
    return cache.get('model:metadata:%s' % urllib.quote(title))


def set_metadata(title, value):
    _set_cache('model:metadata:%s' % urllib.quote(title), value)


def del_rendered_body(title):
    cache.delete('model:rendered_body:%s' % urllib.quote(title))


def del_data(title):
    cache.delete('model:data:%s' % urllib.quote(title))


def del_metadata(title):
    cache.delete('model:metadata:%s' % urllib.quote(title))


def del_hashbangs(title):
    cache.delete('model:hashbangs:%s' % urllib.quote(title))


def set_titles(email, content):
    try:
        add_recent_email(email)
        _set_cache('model:titles:%s' % email, content)
    except:
        pass


def get_titles(email):
    try:
        return cache.get('model:titles:%s' % email)
    except:
        pass


def del_titles():
    try:
        emails = get_recent_emails()
        keys = ['model:titles:%s' % email
                for email in emails + ['None']]
        c.delete_multi(keys)
    except:
        pass


def flush_all():
    cache.clear()