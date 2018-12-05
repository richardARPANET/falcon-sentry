import pytest
import falcon
from falcon.testing.client import simulate_get

from falcon_sentry import falcon_sentry
from falcon_sentry.sentry import _create_error_handler

SDK_PATH = 'falcon_sentry.sentry.sentry_sdk'
DSN = 'https://00000000000000000000000000000000@sentry.io/0000000'


class HappyResource:

    def on_get(self, req, resp):
        resp.body = 'hello world!'
        resp.status = falcon.HTTP_200


class UnhappyResource:
    def on_get(self, req, resp):
        resp.body = 'hello world!'
        resp.status = falcon.HTTP_200
        raise RuntimeError('Something went wrong!')


class BadRequestResource:
    def on_get(self, req, resp):
        raise falcon.HTTPBadRequest('Bad request')


class ServerErrorResource:
    def on_get(self, req, resp):
        raise falcon.HTTPInternalServerError()


@pytest.fixture
def app_with_dsn_passed_in():
    application = falcon.API()
    application.add_route('/hello-world', HappyResource())
    application.add_route('/unhappy', UnhappyResource())
    application.add_route('/400', BadRequestResource())
    application.add_route('/500', ServerErrorResource())
    application = falcon_sentry(dsn=DSN, app=application)
    return application


@pytest.fixture
def app_without_dsn_with_env_var(monkeypatch):
    application = falcon.API()
    application.add_route('/hello-world', HappyResource())
    application.add_route('/unhappy', UnhappyResource())
    application.add_route('/400', BadRequestResource())
    application.add_route('/500', ServerErrorResource())
    monkeypatch.setenv('SENTRY_DSN', DSN)
    # DSN not passed in to ``falcon_sentry`` so it should default
    # to using ENV VAR.
    application = falcon_sentry(app=application)
    return application


@pytest.fixture
def mock_sentry_sdk(mocker):
    return mocker.patch(SDK_PATH)


@pytest.mark.parametrize('app_fixture', [
    'app_with_dsn_passed_in',
    'app_without_dsn_with_env_var',
])
def test_get_endpoint_which_does_not_error(
    app_fixture, request, mock_sentry_sdk
):
    app = request.getfixturevalue(app_fixture)
    result = simulate_get(app, '/hello-world')

    assert result.status == falcon.HTTP_200
    assert result.content == b'hello world!'
    assert not mock_sentry_sdk.capture_exception.called


@pytest.mark.parametrize('app_fixture', [
    'app_with_dsn_passed_in',
    'app_without_dsn_with_env_var',
])
def test_get_endpoint_which_does_error(app_fixture, request, mock_sentry_sdk):
    app = request.getfixturevalue(app_fixture)

    result = simulate_get(app, '/unhappy')

    assert result.status == falcon.HTTP_500
    assert result.content.decode().startswith('A server error occurred')
    assert mock_sentry_sdk.capture_exception.called


@pytest.mark.parametrize('app_fixture', [
    'app_with_dsn_passed_in',
    'app_without_dsn_with_env_var',
])
def test_get_endpoint_which_400_errors(app_fixture, request, mock_sentry_sdk):
    app = request.getfixturevalue(app_fixture)

    result = simulate_get(app, '/400')

    # Checks that for normal exceptions handled by falcon they are
    # not delivered to sentry
    assert result.status == falcon.HTTP_400
    assert result.content == b'{"title": "Bad request"}'
    assert not mock_sentry_sdk.capture_exception.called


@pytest.mark.parametrize('app_fixture', [
    'app_with_dsn_passed_in',
    'app_without_dsn_with_env_var',
])
def test_get_endpoint_which_500_errors(app_fixture, request, mock_sentry_sdk):
    app = request.getfixturevalue(app_fixture)

    result = simulate_get(app, '/500')

    # Falcon 500 errors are delivered to sentry
    assert result.status == falcon.HTTP_500
    assert result.content == b'{"title": "500 Internal Server Error"}'
    mock_sentry_sdk.init.assert_called_once_with(DSN)
    assert mock_sentry_sdk.capture_exception.called


def test_create_error_handler(mocker, mock_sentry_sdk):
    handler = _create_error_handler()
    req = mocker.Mock()
    resp = mocker.Mock()
    ex = RuntimeError('Something went wrong!')

    handler(ex=ex, req=req, resp=resp, params=None)

    # Exception was delivered to Sentry
    assert mock_sentry_sdk.capture_exception.called
    mock_sentry_sdk.capture_exception.assert_called_once_with(ex)

    # Server response is 500 with the default message
    assert resp.status == falcon.HTTP_500
    assert resp.body.startswith('A server error occurred (reference ')


def test_create_error_handler_with_custom_500_message(
    mocker, mock_sentry_sdk
):
    handler = _create_error_handler(error_response_body='Custom message')
    req = mocker.Mock()
    resp = mocker.Mock()
    ex = RuntimeError('Something went wrong!')

    handler(ex=ex, req=req, resp=resp, params=None)

    # Exception was delivered to Sentry
    assert mock_sentry_sdk.capture_exception.called
    mock_sentry_sdk.capture_exception.assert_called_once_with(ex)

    # Server response is 500 with the default message
    assert resp.status == falcon.HTTP_500
    assert resp.body.startswith('Custom message')
