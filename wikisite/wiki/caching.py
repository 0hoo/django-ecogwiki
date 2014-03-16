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


def flush_all():
    cache.clear()