# Copyright (c) 2015 Data King Ltd
# See LICENSE file for license details

from django import template

from accounting import models

register = template.Library()

@register.filter
def currency(amount):
    return models.currency_display(amount)
