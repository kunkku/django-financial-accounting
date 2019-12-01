# Copyright (c) 2015-2019 Data King Ltd
# See LICENSE file for license details

from django import template

from .. import display

register = template.Library()

@register.filter
def currency(amount):
    return display.currency(amount)
