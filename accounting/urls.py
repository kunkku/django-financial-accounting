# Copyright (c) 2015-2019 Data King Ltd
# See LICENSE file for license details

from django.conf.urls import *

from accounting.views import *

app_name = 'accounting'

urlpatterns = (
    url(
        r'^account_chart/(?P<fy>\w+)/$',
        AccountChartView.as_view(),
        name='account_chart'
    ),
    url(
        r'^general-ledger/(?P<fy>\w+)/$',
        GeneralLedgerView.as_view(),
        name='general_ledger'
    ),
    url(
        r'^general-journal/(?P<fy>\w+)/$',
        JournalView.as_view(),
        name='general_journal'
    ),
    url(
        r'^journal/(?P<fy>\w+)/(?P<code>[^/]+)/$',
        JournalView.as_view(),
        name='journal'
    )
)
