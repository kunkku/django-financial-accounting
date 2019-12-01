# Copyright (c) 2015-2019 Data King Ltd
# See LICENSE file for license details

def currency(amount):
    return '{:0.2f}'.format(amount) if amount else '0.00'
