# django-financial-accounting

This project is a double-entry bookkeeping application for
[Django](https://www.djangoproject.com/). It has been tested with Django
release 2.0.

In order to use this application in your Django project, you need to do the
following:

1. Install [django-mptt](https://pypi.org/project/django-mptt/).

2. [Download this application](https://github.com/kunkku/django-financial-accounting/archive/master.zip)
   and extract the `django-financial-accounting/accounting` directory into your
   project's base directory or into any location included in your Python module
   search path.

3. Include `mptt` and `accounting` in the `INSTALLED_APPS` list in your
   project's `settings.py`.

4. Include `accounting.urls` in the `urlpatterns` list in your project's
   `urls.py`, for example as follows:

   `path('accounting/', include('accounting.urls'))`

5. Run `./manage.py migrate` to update the database schema.

6. If your organization's fiscal year differs from the calendar year, create an
   appropriate object for the current fiscal year, defining the start and end
   dates.

7. Create suitable journals and the chart of accounts e.g. by
    * using the Django admin application, or
    * extracting `sample-fixtures.yaml` from the package downloaded in step 2,
     installing [PyYAML](https://pypi.org/project/PyYAML/), and running
     `./manage.py loaddata sample-fixtures.yaml`.

After these steps, you are ready to start entering transactions to the ledger.
This can be done from the admin application or programmatically, e.g. as
follows:

    from accounting.models import *

    txn = Transaction.objects.create(
        journal=Journal.objects.get(code='C'),
        description='Share issue'
    )

    txn.transactionitem_set.create(
        account=Account.objects.get(code='1100'),
        amount=-10000
    )

    txn.transactionitem_set.create(
        account=Account.objects.get(code='3100'),
        amount=10000
    )

    txn.commit()
