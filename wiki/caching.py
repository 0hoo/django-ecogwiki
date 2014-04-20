import urllib
from django.core.cache import cache


def _set_cache(key, value, exp_sec=None):
    if type(key) is str or type(key) is unicode:
        cache.set(urllib.quote(key.encode('utf8')), value)
    else:
        cache.set(key, value)


def _get_cache(key):
    if type(key) is str or type(key) is unicode:
        return cache.get(urllib.quote(key.encode('utf8')))
    else:
        return cache.get(key)


def _del_cache(key):
    if type(key) is str or type(key) is unicode:
        cache.delete(urllib.quote(key.encode('utf8')))
    else:
        cache.delete(key)


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
        emails = _get_cache(key)
        if emails is None:
            cache.clear()
            emails = []
        return emails
    except:
        return []


def get_schema_set():
    return _get_cache('schema_set')


def set_schema_set(value):
    _set_cache('schema_set', value)


def get_schema(key):
    return _get_cache('schema:%s' % key)


def set_schema(key, value):
    _set_cache('schema:%s' % key, value)


def get_schema_itemtypes():
    return _get_cache('schema:itemtypes')


def set_schema_itemtypes(value):
    _set_cache('schema:itemtypes', value)


def get_schema_datatype(type_name):
    return _get_cache('schema:datatype:%s' % type_name)


def set_schema_datatype(type_name, prop):
    _set_cache('schema:datatype:%s' % type_name, prop)


def get_schema_property(prop_name):
    return _get_cache('schema:prop:%s' % prop_name)


def set_schema_property(prop_name, prop):
    _set_cache('schema:prop:%s' % prop_name, prop)


def get_hashbangs(title):
    _get_cache('model:hashbangs:%s' % title)


def set_hashbangs(title, value):
    _set_cache('model:hashbangs:%s' % title, value)


def get_rendered_body(title):
    return _get_cache('model:rendered_body:%s' % title)


def set_rendered_body(title, value):
    if not value:
        return
    _set_cache('model:rendered_body:%s' % title, value)


def get_data(title):
    return _get_cache('model:data:%s' % title)


def set_data(title, value):
    _set_cache('model:data:%s' % title, value)


def get_metadata(title):
    return _get_cache('model:metadata:%s' % title)


def set_metadata(title, value):
    _set_cache('model:metadata:%s' % title, value)


def del_rendered_body(title):
    _del_cache('model:rendered_body:%s' % title)


def del_data(title):
    _del_cache('model:data:%s' % title)


def del_metadata(title):
    _del_cache('model:metadata:%s' % title)


def del_hashbangs(title):
    _del_cache('model:hashbangs:%s' % title)


def set_titles(email, content):
    try:
        add_recent_email(email)
        _set_cache('model:titles:%s' % email, content)
    except:
        pass


def get_titles(email):
    try:
        return _get_cache('model:titles:%s' % email)
    except:
        pass


def del_titles():
    try:
        emails = get_recent_emails()
        for email in emails + ['None']:
            cache.delete('model:titles:%s' % email)
    except:
        pass


def set_schema_selectable_itemtypes(value):
    _set_cache('schema:selectable_itemtypes', value)


def get_schema_selectable_itemtypes():
    return _get_cache('schema:selectable_itemtypes')


def set_cardinalities(key, data):
    try:
        return _set_cache('schema:cardinalities:%s' % key, data)
    except:
        pass


def get_cardinalities(key):
    try:
        return _get_cache('schema:cardinalities:%s' % key)
    except:
        pass


def get_config():
    return _get_cache('model:config')


def set_config(value):
    _set_cache('model:config', value)


def del_config():
    cache.delete('model:config')


def set_wikiquery(q, email, value):
    # adaptive expiration time
    exp_sec = 60
    if type(value) == list:
        if len(value) < 2:
            exp_sec = 60
        elif len(value) < 10:
            exp_sec = 60 * 5
        elif len(value) < 100:
            exp_sec = 60 * 60
        elif len(value) < 500:
            exp_sec = 60 * 60 * 24

    _set_cache('model:wikiquery:%s:%s' % (urllib.quote(q), email), value, exp_sec)


def get_wikiquery(q, email):
    return _get_cache('model:wikiquery:%s:%s' % (urllib.quote(q), email))


def flush_all():
    cache.clear()