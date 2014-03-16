from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name' : 'wiki/login.html', }),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page' : '/'}),
    url(r'^(?P<path>.*)$', views.index, name='index')
)