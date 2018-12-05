falcon-sentry
--------------

Installation
------------

.. code:: bash

    pip install falcon-sentry

How to use
------------

When creating your Falcon application/API instance.
Wrap it with falcon-sentry and pass in your Sentry DSN.

.. code:: python

    application = falcon.API()
    application.add_route('/items', MyResource())
    dsn = 'https://00000000000000000000000000000000@sentry.io/0000000'
    application = falcon_sentry(dsn=dsn, app=application)
    return application

You can also use an environment variable to specify the DSN.

.. code:: python

    os.environ['SENTRY_DSN'] = 'https://00000000000000000000000000000000@sentry.io/0000000'
    application = falcon_sentry(app=application)
    return application

If both the ``dsn`` parameter and the environment variable are missing then falcon-sentry will do nothing and return the application instance.
