# Copyright (c) 2015-2019 Data King Ltd
# See LICENSE file for license details

from django import forms

from .models import *

class TransactionItemForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=Account.objects, required=False, widget=forms.HiddenInput()
    )
    lot = forms.ModelChoiceField(
        queryset=Lot.objects, required=False, widget=forms.HiddenInput()
    )
    amount = forms.DecimalField(
        required=False,
        max_digits=16,
        decimal_places=2,
        widget=forms.HiddenInput()
    )

    target = forms.ChoiceField(label='account and lot')
    debit = forms.DecimalField(
        label='debit', required=False, max_digits=16, decimal_places=2
    )
    credit = forms.DecimalField(
        label='credit', required=False, max_digits=16, decimal_places=2
    )

    class Meta:
        model = TransactionItem
        fields = (
            'target',
            'debit',
            'credit',
            'description',
            'account',
            'lot',
            'amount'
        )

    def __init__(self, *args, **kwargs):
        super(TransactionItemForm, self).__init__(*args, **kwargs)

        targets = [('', '-' * 9)]
        for account in Account.objects.filter(frozen=False).all():
            targets.append((account.pk, str(account)))
            if account.lot_tracking:
                for lot in account.lots():
                    targets.append(
                        (
                            '{} {}'.format(account.pk, lot.pk),
                            '{}: {} ({})'.format(
                                account, lot, lot.balance_display()
                            )
                        )
                    )

        tfield = self.fields['target']
        tfield.choices = targets
        tfield.initial = ''

        item = kwargs.get('instance')
        if not item:
            return

        if item.account:
            target = [item.account]
            if item.lot:
                target.append(item.lot)
            self.fields['target'].initial = ' '.join(
                (str(t.pk) for t in target)
            )

        if item.amount:
            self.fields[
                'credit' if item.amount > 0 else 'debit'
            ].initial = abs(item.amount)
            
    def clean(self):
        target = self.cleaned_data.get('target')
        if target:
            target = target.split()
            self.cleaned_data['account'] = Account.objects.get(pk=target[0])
            self.cleaned_data['lot'] = Lot.objects.get(
                pk=target[1]
            ) if len(target) == 2 else None

        self.cleaned_data['amount'] = (self.cleaned_data['credit'] or 0) - \
                                      (self.cleaned_data['debit'] or 0)

        return self.cleaned_data
