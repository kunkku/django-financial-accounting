# Copyright (c) 2015-2020 Data King Ltd
# See LICENSE file for license details

from django.urls import path

from .views import *

app_name = 'accounting'

urlpatterns = (
    path(
        'account-chart/<str:fy>',
        AccountChartView.as_view(),
        name='account_chart'
    ),
    path(
        'general-ledger/<str:fy>',
        GeneralLedgerView.as_view(),
        name='general_ledger'
    ),
    path(
        'general-journal/<str:fy>',
        JournalView.as_view(),
        name='general_journal'
    ),
    path('journal/<str:fy>/<str:code>', JournalView.as_view(), name='journal')
)
