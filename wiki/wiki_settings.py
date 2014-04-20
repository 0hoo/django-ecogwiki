VERSION = '0.0.1_20140407_0'

DEFAULT_CONFIG = {
    'navigation': [
        {
            'name': 'Home',
            'url': '/Home',
        },
        {
            'name': 'Changes',
            'url': '/sp.changes',
            'shortcut': 'C',
        },
    ],
    'admin': {
        'email': '',
        'gplus_url': '',
        'twitter': '',
    },
    'service': {
        'title': '',
        'domain': '',
        'fb_app_id': '',
        'ga_profile_id': '',
        'ga_classic_profile_id': '',
        'css_list': [
            '/static/css/base.css',
        ],
        'default_permissions': {
            'read': ['all'],
            'write': ['login'],
        },
    }
}