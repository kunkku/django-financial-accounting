# Copyright (c) 2015-2019 Data King Ltd
# See LICENSE file for license details

from django.contrib import admin, messages
from mptt.admin import MPTTModelAdmin

from .models import *
from .forms import *


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

    @staticmethod
    def action(method, order, message):
        def f(self, request, queryset):
            for obj in queryset.order_by(*order).all():
                try:
                    getattr(obj, method)()
                    messages.success(request, message.format(obj))
                except ValidationError as e:
                    messages.error(request, ', '.join(e.messages))
                    break
        f.short_description = method.capitalize()
        return f


class FiscalYearAdmin(ContextAdmin):
    model = FiscalYear
    list_display = (FiscalYear.__str__, 'start', 'end', 'closed')
    actions = (
        ContextAdmin.action(
            'close', ('end',), 'Books closed for fiscal year {}'
        ),
    )

    def get_context(self, fy):
        return {
            'fy': str(fy),
            'journals': (j.code for j in Journal.objects.all())
        }

admin.site.register(FiscalYear, FiscalYearAdmin)


class AccountAdmin(ContextMixin, MPTTModelAdmin):
    list_display = (
        'name',
        'code',
        'type',
        'frozen',
        'lot_tracking',
        Account.balance_display
    )

    def get_context(self, account):
        return {'transactions': account.transactions(), 'account': account}

admin.site.register(Account, AccountAdmin)


class LotAdmin(ContextAdmin):
    model = Lot
    list_display = (Lot.__str__, 'account', Lot.balance_display)
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
    list_display = ('code', 'description')
    change_form_template = 'accounting/transaction_list.html'

    def get_context(self, journal):
        return {'transactions': journal.transactions()}

admin.site.register(Journal, JournalAdmin)


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    form = TransactionItemForm

class TransactionAdmin(ContextAdmin):
    model = Transaction
    ordering = ('-state', '-date', '-journal__code', '-number', '-id')
    list_display = (
        Transaction.__str__, 'state', 'date', Transaction.balance_display
    )
    list_filter = ('state',)
    inlines = (TransactionItemInline,)
    actions = (
        ContextAdmin.action(
            'commit', ('date', 'id'), 'Transaction {} committed'
        ),
    )

    def get_context(self, txn):
        return {
            'transactions': [txn], 'title': txn
        } if txn.state == 'C' else {}

admin.site.register(Transaction, TransactionAdmin)


admin.site.register(FiscalPeriod, admin.ModelAdmin)
