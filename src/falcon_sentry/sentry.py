
import json
import os
import logging

import falcon
import sentry_sdk

logger = logging.getLogger(__name__)


def _create_error_handler(*, dsn=None, error_response_body=None, **extra):
    sentry_sdk.init(dsn, **extra)

    def _get_error_response_body(error_reference):
        return error_response_body or (
            f'A server error occurred (reference code: {error_reference}"). '
            'Please contact the administrator.'
        )

    def internal_error_handler(ex, req, resp, params):

        if isinstance(ex, falcon.HTTPError):
            resp.status = ex.status
            resp.body = json.dumps(ex.to_dict())
            if isinstance(ex, falcon.HTTPInternalServerError):
                sentry_sdk.capture_exception(ex)
            else:
                raise
        else:
            error_reference = sentry_sdk.capture_exception(ex)
            error_response_body = _get_error_response_body(error_reference)
            resp.status = falcon.HTTP_500
            resp.body = error_response_body
    return internal_error_handler


def falcon_sentry(app, dsn=None, error_response_body=None, **extra):
    # SENTRY_DSN env var, or arg
    try:
        dsn = dsn or os.environ['SENTRY_DSN']
    except KeyError:
        logger.warning(
            'No Sentry DSN given or found in environment variable SENTRY_DSN, '
            'skipping adding of error handler...'
        )
        return app
    app.add_error_handler(
        Exception,
        _create_error_handler(
            dsn=dsn, error_response_body=error_response_body, **extra
        )
    )
    return app
