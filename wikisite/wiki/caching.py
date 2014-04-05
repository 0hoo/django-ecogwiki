from django.core.cache import cache


def get_schema_set():
    return cache.get('schema_set')


def set_schema_set(value):
    cache.set('schema_set', value)


def get_schema(key):
    return cache.get('schema:%s' % key)


def set_schema(key, value):
    cache.set('schema:%s' % key, value)


def get_schema_itemtypes():
    return cache.get('schema:itemtypes')


def set_schema_itemtypes(value):
    cache.set('schema:itemtypes', value)


def get_schema_datatype(type_name):
    return cache.get('schema:datatype:%s' % type_name)


def set_schema_datatype(type_name, prop):
    cache.set('schema:datatype:%s' % type_name, prop)


def get_schema_property(prop_name):
    return cache.get('schema:prop:%s' % prop_name)


def set_schema_property(prop_name, prop):
    cache.set('schema:prop:%s' % prop_name, prop)


def get_hashbangs(title):
    cache.get('model:hashbangs:%s' % title)


def set_hashbangs(title, value):
    cache.set('model:hashbangs:%s' % title, value)


def get_rendered_body(title):
    return cache.get('model:rendered_body:%s' % title)


def set_rendered_body(title, value):
    if not value:
        return
    cache.set('model:rendered_body:%s' % title, value)


def get_data(title):
    return cache.get('model:data:%s' % title)


def set_data(title, value):
    cache.set('model:data:%s' % title, value)


def get_metadata(title):
    return cache.get('model:metadata:%s' % title)


def set_metadata(title, value):
    cache.set('model:metadata:%s' % title, value)


def del_rendered_body(title):
    cache.delete('model:rendered_body:%s' % title)


def del_data(title):
    cache.delete('model:data:%s' % title)


def del_metadata(title):
    cache.delete('model:metadata:%s' % title)


def del_hashbangs(title):
    cache.delete('model:hashbangs:%s' % title)


def del_titles():
    pass


def flush_all():
    cache.clear()