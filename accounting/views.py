# Copyright (c) 2015 Data King Ltd
# See LICENSE file for license details

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from datetime import date, timedelta

from accounting.models import *


class LedgerView(TemplateView):

    def get_context_data(self, **kwargs):
        fy = int(kwargs['fy'])
        fy = get_object_or_404(
            FiscalYear,
            start__gt=date(fy - 1, 12, 31),
            end__lt=date(fy + 1, 1, 1)
        )

        res = super(LedgerView, self).get_context_data(**kwargs)
        res['title'] = '{} {}'.format(self.title, fy)
        res.update(self.get_fy_context(fy))
        return res


class GeneralJournalView(LedgerView):
    title = 'General Journal'
    template_name = 'accounting/general_journal.html'

    def get_fy_context(self, fy):
        return {'transactions': Transaction.objects.filter(fiscal_year=fy)}


class GeneralLedgerView(LedgerView):
    title = 'General Ledger'
    template_name = 'accounting/general_ledger.html'

    def get_fy_context(self, fy):
        return {
            'fy': fy,
            'accounts': (
                (
                    account,
                    account.balance(fy.start - timedelta(1)) * account.sign(),
                    account.transactions().filter(fiscal_year=fy),
                    account.balance(fy.end) * account.sign()
                ) for account in Account.objects.all()
            )
        }
