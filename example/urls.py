# Copyright (c) 2015-2022 Data King Ltd
# See LICENSE file for license details

from django.contrib import admin
from django.urls import include, path

admin.site.site_title = 'Example'
admin.site.site_header = 'Example'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounting/', include('accounting.urls'))
]
