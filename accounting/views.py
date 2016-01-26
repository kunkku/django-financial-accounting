# Copyright (c) 2015-2016 Data King Ltd
# See LICENSE file for license details

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from datetime import date, timedelta

from accounting.models import *


class LedgerView(TemplateView):

    def get_context_data(self, **kwargs):
        res = super(LedgerView, self).get_context_data(**kwargs)

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


class GeneralLedgerView(LedgerView):
    template_name = 'accounting/general_ledger.html'

    def update_context(self, context, args):
        context['title'] = 'General Ledger'

        fy = context['fy']
        context['accounts'] = (
            (
                account,
                account.balance(fy.start - timedelta(1)) * account.sign(),
                account.transactions().filter(fiscal_year=fy),
                account.balance(fy.end) * account.sign()
            ) for account in Account.objects.all()
        )


class JournalView(LedgerView):
    template_name = 'accounting/journal.html'

    def update_context(self, context, args):
        context['title'] = 'General Journal'
        txn_filter = {'fiscal_year': context['fy']}

        if 'code' in args:
            journal = get_object_or_404(Journal, code=args['code'])
            context['title'] = journal.description or journal.code
            txn_filter['journal'] = journal

        context['transactions'] = Transaction.objects.filter(**txn_filter)
