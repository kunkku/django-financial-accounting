# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.html import format_html, mark_safe

from mptt.utils import tree_item_iterator

from collections.abc import Iterable
from datetime import timedelta

from .. import display

register = template.Library()

@register.filter
def currency(amount):
    return display.currency(amount)

def adjusted_balance(account, **kwargs):
    return account.balance(**kwargs) * account.sign()

@register.filter
def opening_balance(account, fy):
    return adjusted_balance(
        account, date=fy.start - timedelta(days=1), include_closing=True
    )

@register.filter
def closing_balance(account, fy):
    return adjusted_balance(account, date=fy.end)

@register.filter
def transactions(account, fy):
    return account.transactions().filter(fiscal_year=fy, closing=False)


INDENT = '<td class="indent"></td>'

@register.simple_tag
def account_chart(accounts, fy, include_closing=False, zero_rows=True):
    fyears = fy if isinstance(fy, Iterable) else (fy,)

    stack = [([],)]
    show = 0
    max_show = 1

    def flush():
        nonlocal stack, show
        spec = stack.pop()
        if len(stack) == show:
            stack[-1][0].append(spec)
            show -= 1

    for account, info in tree_item_iterator(accounts):
        if not info['new_level']:
            flush()

        balances = [
            account.balance_subtotal(
                date=fy.end, include_closing=include_closing
            ) * account.sign() for fy in fyears
        ]
        if zero_rows or any(balances):
            show = len(stack)
            max_show = max(max_show, show)
        stack.append(([], account, balances))

        for _ in info['closed_levels']:
            flush()

    def render(specs, level):
        span = max_show - level
        left_pad = mark_safe(INDENT * level)
        right_pad = mark_safe(INDENT * (span - 1))

        res = ''

        for children, account, balances in specs:
            res += format_html(
                '<tr>{indent}<td colspan="{span}">{account}</td>{balances}</tr>{children}',
                account=account,
                balances=mark_safe(
                    ''.join(
                        format_html(
                            '{left_pad}<td class="currency">{balance}</td>{right_pad}',
                            balance=display.currency(balance),
                            left_pad=left_pad,
                            right_pad=right_pad
                        ) for balance in balances
                    )
                ),
                children=render(children, level + 1),
                indent=left_pad,
                span=span
            )

        return mark_safe(res)

    return format_html('<table>{}</table>', render(stack[0][0], 0))
