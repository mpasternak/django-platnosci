# -*- encoding: utf-8 -*-

from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url

urlpatterns = patterns('platnosci.views',
                       url(r'^status/$', 'payment_status_view', name = 'payment_status_view'))
