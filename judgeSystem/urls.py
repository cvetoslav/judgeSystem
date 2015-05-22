from django.conf.urls import patterns, include, url
from django.contrib import admin

from judge import urls

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'judgeSystem.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^judge/', include('judge.urls', namespace = 'judge')),
)
