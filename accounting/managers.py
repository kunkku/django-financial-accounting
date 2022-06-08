# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from mptt.managers import TreeManager

class AccountManager(TreeManager):

    def __init__(self, *types):
        super().__init__()
        self.types = types

    def get_queryset(self):
        qs = super().get_queryset()
        if self.types:
            qs = qs.filter(type__in=self.types)
        return qs
