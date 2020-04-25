# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django.urls import path

from .views import *

app_name = 'accounting'

urlpatterns = (
    path(
        'balance-sheet/<str:fy>',
        BalanceSheetView.as_view(),
        name='balance_sheet'
    ),
    path(
        'income-statement/<str:fy>',
        IncomeStatementView.as_view(),
        name='income_statement'
    ),
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
