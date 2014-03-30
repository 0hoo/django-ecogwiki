from django.conf.urls import patterns, url, include

import views

urlpatterns = patterns('',
    #url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name' : 'wiki/login.html', }),
    #url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page' : '/'}),
    url(r'^accounts/register/$', views.WikiRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'^(?P<path>.*)$', views.index, name='index'),
    #url(r'^accounts/signup/$', views.signup),
)