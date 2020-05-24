# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django import template
from django.utils.html import format_html, mark_safe

from mptt.utils import previous_current_next

from collections.abc import Iterable
from datetime import timedelta
from itertools import count

from .. import display

register = template.Library()

@register.filter
def currency(amount):
    return display.currency(amount)

def adjusted_balance(account, **kwargs):
    return account.get_balance(**kwargs) * account.sign

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
    return account.transactions.filter(fiscal_year=fy, closing=False)


@register.simple_tag
def account_chart(
    accounts,
    fy,
    include_closing=False,
    lots=False,
    post_totals=False,
    signed=False,
    zero_rows=True
):
    fyears = tuple(fy) if isinstance(fy, Iterable) else (fy,)

    stack = [([],)]
    show = 0
    max_show = 1
    first = None

    def append(account):
        nonlocal stack, show, max_show
        balances = [
            account.get_total_balance(
                date=fy.end, include_closing=include_closing
            ) * (1 if signed else account.sign) for fy in fyears
        ]
        if zero_rows or any(balances):
            show = len(stack)
            max_show = max(max_show, show)
        stack.append(([], account, balances))

    def flush():
        nonlocal stack, show
        spec = stack.pop()
        if len(stack) == show:
            stack[-1][0].append(spec)
            show -= 1
        return spec[1]

    for _, acct, next_acct in previous_current_next(accounts):
        if not first:
            first = acct

        append(acct)
        if lots:
            for lot in acct.get_lots():
                append(lot)
                flush()

        ancs = list((next_acct or first).get_ancestors())
        if not next_acct:
            for anc in acct.get_ancestors(ascending=True):
                if anc in ancs:
                    ancs.remove(anc)
                    break

        while stack[-1][1] not in ancs:
            acc = flush()
            if len(stack) == 1:
                parent = acc.parent
                if not parent or parent in ancs:
                    break
                append(parent)

    empty_cols = ('',) * len(fyears)

    def render(specs, level, right_cols):
        indent = mark_safe('<td class="indent"></td>' * level)

        left_span = max_show - len(right_cols) - 1
        left_col = mark_safe(
            format_html('<td colspan="{}">', left_span) if left_span else ''
        )

        res = ''

        for i, (children, account, balances) in zip(count(), specs):
            last = i == len(specs) - 1
            if post_totals:
                child_rcols = (
                    [
                        [display.currency(balance) for balance in balances]
                    ] if len(children) > 1 else []
                ) + [
                    fy_rcols if last else empty_cols for fy_rcols in right_cols
                ]
            else:
                child_rcols = right_cols[1:]

            res += format_html(
                '<tr>{indent}<td colspan="{span}">{account}</td>{balances}</tr>{children}',
                account=account,
                balances='' if post_totals and children else mark_safe(
                    ''.join(
                        format_html(
                            '{left_col}<td class="currency">{balance}</td>{right_cols}',
                            balance=display.currency(balance),
                            left_col=left_col,
                            right_cols=mark_safe(
                                ''.join(
                                    format_html(
                                        '<td class="currency">{}</td>',
                                        fy_rcols[j] if last else ''
                                    ) for fy_rcols in right_cols
                                )
                            )
                        ) for j, balance in zip(count(), balances)
                    )
                ),
                children=render(children, level + 1, child_rcols),
                indent=indent,
                span=max_show - level
            )

        return mark_safe(res)

    return format_html(
        '<table>{}</table>',
        render(
            stack[0][0],
            0,
            () if post_totals else (empty_cols,) * (max_show - 1)
        )
    )
