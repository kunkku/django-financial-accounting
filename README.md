# django-financial-accounting

This project is a double-entry bookkeeping application for
[Django](https://www.djangoproject.com/). It has been tested with Django
release 1.9.

In order to use this application in your Django project, you need to do the
following:

1. Install [django-mptt](https://pypi.python.org/pypi/django-mptt).

2. [Download this application](https://github.com/kunkku/django-financial-accounting/archive/master.zip)
   and extract the `django-financial-accounting/accounting` directory into your
   project's base directory or into any location included in your Python module
   search path.

3. Include `mptt` and `accounting` in the `INSTALLED_APPS` list in your
   project's `settings.py`.

4. Include `accounting.urls` in the `urlpatterns` list in your project's
  `urls.py`, for example as follows:
 
  `url(r'^accounting/', include('accounting.urls'))`

5. Run `./manage.py migrate` to update the database schema.

6. Create suitable journals and the chart of accounts e.g. using the Django
   admin application.

After these steps, you are ready to start entering transactions to the ledger.
