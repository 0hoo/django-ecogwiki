VERSION = '0.0.1_20140117_1'

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
            '/statics/css/base.css',
        ],
        'default_permissions': {
            'read': ['all'],
            'write': ['login'],
        },
    },
    'highlight': {
        'style': 'default',
        'supported_languages': [
            'sh',
            'csharp',
            'c++',
            'css',
            'coffeescript',
            'diff',
            'html',
            'xml',
            'json',
            'java',
            'javascript',
            'makefile',
            'markdown',
            'objectivec',
            'php',
            'perl',
            'python',
            'ruby',
            'sql',
        ]
    }
}