from __future__ import unicode_literals

from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.views.i18n import set_language

from mezzanine.core.views import direct_to_template
from mezzanine.conf import settings

import seek.urls
import api_app.urls

from . import views

admin.autodiscover()

urlpatterns = i18n_patterns(
    url(r'^login', views.login_seek, name="login_seek"),
    url(r'^logout$', views.logout_seek, name="logout_seek"),
    url(r'^signup/', views.signup_seek, name="signup_seek"),
    
    url("^admin/", include(admin.site.urls)),
    url("^seek/", include(seek.urls)),
    url("^api/", include(api_app.urls)),
)

if settings.USE_MODELTRANSLATION:
    urlpatterns += [
        url('^i18n/$', set_language, name='set_language'),
    ]

urlpatterns += [
    url("^$", direct_to_template, {"template": "index.html"}, name="home"),
    url("^", include("mezzanine.urls")),
    url(r'^accounts/login/', views.login_seek, name="login_seek"),
    url(r'^accounts/signup/', views.signup_seek, name="signup_seek"),
    
]

handler404 = "mezzanine.core.views.page_not_found"
handler500 = "mezzanine.core.views.server_error"
