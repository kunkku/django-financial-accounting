# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from datetime import date, timedelta

from .models import *


class ReportView(TemplateView):

    def get_context_data(self, **kwargs):
        res = super(ReportView, self).get_context_data(**kwargs)
        fy = kwargs['fy']

        try:
            y = int(fy)
            i = 0
        except ValueError:
            y = int(fy[:-1])
            i = ord(fy[-1]) - 64

        try:
            fy = FiscalYear.objects.filter(
                end__gte=date(y, 1, 1), end__lte=date(y, 12, 31)
            ).order_by('end')[i]
        except IndexError:
            raise Http404

        res['fy'] = fy
        res['title'] = '{} {}'.format(self.title, fy)
        self.update_context(res, kwargs)
        return res


class AccountView(ReportView):

    def update_context(self, context, args):
        context['accounts'] = Account.objects.all()

class AccountChartView(AccountView):
    title = 'Chart of Accounts'
    template_name = 'accounting/account_chart.html'

    def update_context(self, context, args):
        super(AccountChartView, self).update_context(context, args)
        context['zero_rows'] = True

class GeneralLedgerView(AccountView):
    title = 'General Ledger'
    template_name = 'accounting/general_ledger.html'


class JournalView(ReportView):
    title = 'General Journal'
    template_name = 'accounting/journal.html'

    def update_context(self, context, args):
        txn_filter = {'fiscal_year': context['fy']}

        if 'code' in args:
            journal = get_object_or_404(Journal, code=args['code'])
            context['title'] = journal.description or journal.code
            txn_filter['journal'] = journal

        context['transactions'] = Transaction.objects.filter(**txn_filter)


class AnnualReportView(AccountChartView):
    breakdown = False

    def update_context(self, context, args):
        if not self.breakdown:
            fy = context['fy']
            try:
                context['fy'] = (
                    fy, FiscalYear.by_date(fy.start - timedelta(days=1))
                )
            except FiscalYear.DoesNotExist:
                pass

        accounts = Account.objects.filter(type__in=self.account_types)
        if not self.breakdown:
            accounts = accounts.filter(public=True)

        context['accounts'] = accounts
        context['include_closing'] = 'NE' in self.account_types
        context['lots'] = self.breakdown
        context['post_totals'] = True
        context['signed'] = 'Ex' in self.account_types
        context['zero_rows'] = False

class BalanceSheetView(AnnualReportView):
    title = 'Balance Sheet'
    account_types = ('As', 'Eq', 'NE', 'Li')

class IncomeStatementView(AnnualReportView):
    title = 'Income Statement'
    account_types = ('In', 'Ex')

class BalanceSheetBreakdownView(BalanceSheetView):
    title = 'Balance Sheet Breakdown'
    breakdown = True
