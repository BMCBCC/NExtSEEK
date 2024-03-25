from django.urls import re_path
from django.conf.urls import include

from rest_framework.urlpatterns import format_suffix_patterns
from .views import SamplesViews

from .views import SamplesListViews, SamplesDetailViews, DatafilesListViews, DatafilesDetailViews, DatafileViews

from .views import SamplesViews


urlpatterns = [
    re_path(r'^samples/$', SamplesListViews.as_view()),
    re_path(r'^samples/(?P<pk>[0-9]+)/$', SamplesDetailViews.as_view()),
    re_path(r'^datafiles/$', DatafilesListViews.as_view()),
    re_path(r'^datafiles/(?P<pk>[0-9]+)/$', DatafilesDetailViews.as_view()),
    re_path(r'^rest-auth/', include('rest_auth.urls')),
    re_path(r'^sampleupload/$', SamplesViews.as_view(), name='sample-upload'),
    re_path(r'^datafileupload/$', DatafileViews.as_view(), name='datafile-upload'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
