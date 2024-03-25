from django.conf.urls import url, include

from rest_framework.urlpatterns import format_suffix_patterns
from .views import SamplesViews

from .views import SamplesListViews, SamplesDetailViews, DatafilesListViews, DatafilesDetailViews, DatafileViews

from .views import SamplesViews


urlpatterns = [
    url(r'^samples/$', SamplesListViews.as_view()),
    url(r'^samples/(?P<pk>[0-9]+)/$', SamplesDetailViews.as_view()),
    url(r'^datafiles/$', DatafilesListViews.as_view()),
    url(r'^datafiles/(?P<pk>[0-9]+)/$', DatafilesDetailViews.as_view()),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^sampleupload/$', SamplesViews.as_view(), name='sample-upload'),
    url(r'^datafileupload/$', DatafileViews.as_view(), name='datafile-upload'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
