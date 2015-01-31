# Copyright (c) 2015 Data King Ltd
# See LICENSE file for license details

from django.conf.urls import *

from accounting.views import *

urlpatterns = patterns(
    '',
    url(
        r'^general-journal/(?P<fy>\d+)/$',
        GeneralJournalView.as_view(),
        name='general_journal'
    ),
    url(
        r'^general-ledger/(?P<fy>\d+)/$',
        GeneralLedgerView.as_view(),
        name='general_ledger'
    )
)
