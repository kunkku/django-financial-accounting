# Copyright (c) 2015-2023 Data King Ltd
# See LICENSE file for license details

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

if hasattr(settings, 'ACCOUNTING_COMPANY_NAME'):
    company_name = settings.ACCOUNTING_COMPANY_NAME
    admin.site.site_title = company_name
    admin.site.site_header = company_name

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounting/', include('accounting.urls'))
]
