from django.conf.urls import patterns, url, include

import views

urlpatterns = patterns('',
    url(r'^accounts/register/$', views.WikiRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'^(?P<path>.*)$', views.index, name='index'),
)