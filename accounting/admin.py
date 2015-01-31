# Copyright (c) 2015 Data King Ltd
# See LICENSE file for license details

from django.contrib import admin, messages
from mptt.admin import MPTTModelAdmin

from accounting.models import *
from accounting.forms import *


class ContextMixin(object):

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.model.objects.get(pk=object_id)
        extra_context = extra_context or {}
        extra_context.update(self.get_context(obj))

        cls = type(self)
        while True:
            for base in cls.__bases__:
                if base == admin.ModelAdmin:
                    return base.change_view(
                        self, request, object_id, form_url, extra_context
                    )
                if issubclass(base, admin.ModelAdmin):
                    cls = base
                    break
            else:
                assert False

class ContextAdmin(ContextMixin, admin.ModelAdmin):
    pass


class FiscalYearAdmin(ContextAdmin):
    model = FiscalYear

    def get_context(self, fy):
        return {'fy': unicode(fy)}

admin.site.register(FiscalYear, FiscalYearAdmin)


class AccountAdmin(ContextMixin, MPTTModelAdmin):
    list_display = ('name', 'code', 'type', Account.balance_display)

    def get_context(self, account):
        return {'transactions': account.transactions(), 'account': account}

admin.site.register(Account, AccountAdmin)


class LotAdmin(ContextAdmin):
    model = Lot
    list_display = (Lot.__unicode__, 'account', Lot.balance_display)
    change_form_template = 'accounting/transaction_list.html'

    def get_context(self, lot):
        return {
            'transactions': lot.transactions(),
            'account': lot.account,
            'lot': lot
        }

admin.site.register(Lot, LotAdmin)


class JournalAdmin(ContextAdmin):
    model = Journal
    change_form_template = 'accounting/transaction_list.html'

    def get_context(self, journal):
        return {'transactions': journal.transactions()}

admin.site.register(Journal, JournalAdmin)


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    form = TransactionItemForm

class TransactionAdmin(ContextAdmin):
    model = Transaction
    ordering = ('-state', '-date', '-journal', '-number', '-id')
    list_display = (
        Transaction.__unicode__, 'state', 'date', Transaction.balance
    )
    list_filter = ('state',)
    inlines = (TransactionItemInline,)
    actions = ('commit',)

    def get_context(self, txn):
        return {
            'transactions': [txn], 'title': txn
        } if txn.state == 'C' else {}

    def commit(self, request, queryset):
        for txn in queryset.order_by('date', 'id').all():
            try:
                txn.commit()
                messages.success(
                    request, 'Transaction {} committed'.format(txn)
                )
            except ValidationError, e:
                messages.error(
                    request,
                    'Transaction {}: {}'.format(txn, ', '.join(e.messages))
                )
                break

admin.site.register(Transaction, TransactionAdmin)


admin.site.register(FiscalPeriod, admin.ModelAdmin)
