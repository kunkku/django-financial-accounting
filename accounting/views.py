# Copyright (c) 2015-2016 Data King Ltd
# See LICENSE file for license details

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from datetime import date, timedelta

from accounting.models import *


class ReportView(TemplateView):

    def get_context_data(self, **kwargs):
        res = super(ReportView, self).get_context_data(**kwargs)

        fy = int(kwargs['fy'])
        fy = get_object_or_404(
            FiscalYear,
            start__gt=date(fy - 1, 12, 31),
            end__lt=date(fy + 1, 1, 1)
        )
        res['fy'] = fy

        self.update_context(res, kwargs)
        res['title'] += ' {}'.format(fy)
        return res


class AccountView(ReportView):

    def update_context(self, context, args):
        context['title'] = self.title

        fy = context['fy']
        context['accounts'] = (
            {
                'model': account,
                'opening_balance': self.get_balance(
                    account, fy.start - timedelta(1)
                ),
                'closing_balance': self.get_balance(account, fy.end),
                'transactions': account.transactions().filter(fiscal_year=fy),
                'indentation': '&nbsp;' * 10 * account.get_level()
            } for account in Account.objects.all()
        )


class AccountChartView(AccountView):
    title = 'Chart of Accounts'
    template_name = 'accounting/account_chart.html'

    def get_balance(self, account, date):
        return account.balance_display(date)


class GeneralLedgerView(AccountView):
    title = 'General Ledger'
    template_name = 'accounting/general_ledger.html'

    def get_balance(self, account, date):
        return account.balance(date) * account.sign()


class JournalView(ReportView):
    template_name = 'accounting/journal.html'

    def update_context(self, context, args):
        context['title'] = 'General Journal'
        txn_filter = {'fiscal_year': context['fy']}

        if 'code' in args:
            journal = get_object_or_404(Journal, code=args['code'])
            context['title'] = journal.description or journal.code
            txn_filter['journal'] = journal

        context['transactions'] = Transaction.objects.filter(**txn_filter)
