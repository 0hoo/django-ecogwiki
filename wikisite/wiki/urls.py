from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView

import views

urlpatterns = patterns('',
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset',
        {'post_reset_redirect' : '/accounts/password/reset/done/'}, name='password_reset'),
    (r'^accounts/password/reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    url(r'^accounts/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'post_reset_redirect' : '/accounts/password/done/'}, name='password_reset_confirm'),
    (r'^accounts/password/done/$', 'django.contrib.auth.views.password_reset_complete'),
    url(r'^accounts/info/$', TemplateView.as_view(template_name='registration/info.html')),
    url(r'^accounts/register/$', views.WikiRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'sp\.(.*)', views.special),
    url(r'=(.*)', views.wikiquery),
    url(r'([+-].*)', views.related),
    url(r'^(?P<path>.*)$', views.index, name='index'),
)