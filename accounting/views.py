# Copyright (c) 2015-2024 Data King Ltd
# See LICENSE file for license details

from django.conf import settings
from django.db.models import Max, Min
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from datetime import date

from .models import *


class ReportView(TemplateView):
    def get_context_data(self, **kwargs):
        res = super().get_context_data(**kwargs)
        fy = kwargs['fy']

        try:
            y = int(fy)
            i = 0
        except ValueError:
            try:
                y = int(fy[:-1])
                i = ord(fy[-1]) - 64
            except ValueError:
                raise Http404

        try:
            fy = FiscalYear.objects.filter(
                end__gte=date(y, 1, 1), end__lte=date(y, 12, 31)
            ).order_by('end')[i]
        except IndexError:
            raise Http404

        res['company_name'] = getattr(settings, 'ACCOUNTING_COMPANY_NAME', None)
        res['title'] = self.title
        res['fy'] = fy

        self.update_context(res, kwargs)
        return res


class AccountView(ReportView):
    accounts = Account.objects

    def update_context(self, context, args):
        context['accounts'] = self.accounts.all()

class EquityChangeStatementView(AccountView):
    title = _('Statement of Changes in Equity')
    template_name = 'accounting/equity_change_statement.html'
    accounts = Account.equity_accounts.filter(public=True)

class BalanceSheetBreakdownView(AccountView):
    title = _('Balance Sheet Breakdown')
    template_name = 'accounting/balance_sheet_breakdown.html'
    accounts = Account.balance_accounts

class AccountChartView(AccountView):
    title = _('Chart of Accounts')
    template_name = 'accounting/account_chart.html'

    def update_context(self, context, args):
        super().update_context(context, args)
        context['zero_rows'] = True

class GeneralLedgerView(AccountView):
    title = _('General Ledger')
    template_name = 'accounting/general_ledger.html'


class AnnualReportView(AccountView):
    def update_context(self, context, args):
        super().update_context(context, args)
        context['fiscal_years'] = FiscalYear.objects.filter(
            end__lte=context['fy'].end
        ).order_by('-end')

class FinancialStatementView(AnnualReportView):
    title = _('Financial Statement')
    template_name = 'accounting/financial_statement.html'

    def update_context(self, context, args):
        super().update_context(context, args)
        for group in ('balance', 'pl', 'equity'):
            attr = f'{group}_accounts'
            context[attr] = getattr(Account, attr).filter(public=True)
        context['journals'] = Journal.objects.filter(
            transaction__fiscal_year=context['fy']
        ).values('code', 'description').annotate(
            min=Min('transaction__number'), max=Max('transaction__number')
        )


class BalanceSheetView(AnnualReportView):
    title = _('Balance Sheet')
    template_name = 'accounting/balance_sheet.html'
    accounts = Account.balance_accounts.filter(public=True)

class IncomeStatementView(AnnualReportView):
    title = _('Income Statement')
    template_name = 'accounting/income_statement.html'
    accounts = Account.pl_accounts.filter(public=True)


class JournalView(ReportView):
    title = _('General Journal')
    template_name = 'accounting/journal.html'

    def update_context(self, context, args):
        txn_filter = {'fiscal_year': context['fy']}

        if 'code' in args:
            context['code'] = args['code']
            journal = get_object_or_404(Journal, code=args['code'])
            context['title'] = journal.description or journal.code
            txn_filter['journal'] = journal

        context['transactions'] = Transaction.objects.filter(**txn_filter)
