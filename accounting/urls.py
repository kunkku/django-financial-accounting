# Copyright (c) 2015-2023 Data King Ltd
# See LICENSE file for license details

from django.urls import path

from .views import *

app_name = 'accounting'

urlpatterns = (
    path(
        'financial-statement/<str:fy>',
        FinancialStatementView.as_view(),
        name='financial_statement'
    ),
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
        'equity-change-statement/<str:fy>',
        EquityChangeStatementView.as_view(),
        name='equity_change_statement'
    ),
    path(
        'balance-sheet-breakdown/<str:fy>',
        BalanceSheetBreakdownView.as_view(),
        name='balance_sheet_breakdown'
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
