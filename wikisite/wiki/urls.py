from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView

import views

urlpatterns = patterns('',
    url(r'^accounts/info/$', TemplateView.as_view(template_name='registration/info.html')),
    url(r'^accounts/register/$', views.WikiRegistrationView.as_view(), name='registration_register'),
    url(r'^accounts/', include('registration.backends.simple.urls')),
    url(r'^(?P<path>.*)$', views.index, name='index'),
)