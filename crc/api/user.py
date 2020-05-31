import json

import connexion
import flask
from flask import redirect, g, request

from crc import app, db
from crc.api.common import ApiError
from crc.models.user import UserModel, UserModelSchema
from crc.services.ldap_service import LdapService, LdapUserInfo
from crc.services.approval_service import ApprovalService

"""
.. module:: crc.api.user
   :synopsis: Single Sign On (SSO) user login and session handlers
"""


def verify_token(token=None):
    """
        Verifies the token for the user (if provided). If in production environment and token is not provided,
        gets user from the SSO headers and returns their token.

        Args:
            token: Optional[str]

        Returns:
            token: str

        Raises:
            ApiError.  If not on production and token is not valid, returns an 'invalid_token' 403 error.
            If on production and user is not authenticated, returns a 'no_user' 403 error.
   """
    print('=== verify_token ===')
    print('_is_production()', _is_production())

    failure_error = ApiError("invalid_token", "Unable to decode the token you provided.  Please re-authenticate", status_code=403)

    if not _is_production():
        g.user = UserModel.query.first()
        token = g.user.encode_auth_token()

    if token:
        try:
            token_info = UserModel.decode_auth_token(token)
            g.user = UserModel.query.filter_by(uid=token_info['sub']).first()
        except:
            raise failure_error
        if g.user is not None:
            return token_info
        else:
            raise failure_error

    # If there's no token and we're in production, get the user from the SSO headers and return their token
    if not token and _is_production():
        uid = _get_request_uid()

        if uid is not None:
            db_user = UserModel.query.filter_by(uid=uid).first()

            if db_user is not None:
                g.user = db_user
                token = g.user.encode_auth_token().decode()
                token_info = UserModel.decode_auth_token(token)
                return token_info

            else:
                ApiError("no_user", "User not found. Please login via the frontend app before accessing this feature.", status_code=403)
                raise failure_error


def verify_token_admin(token=None):
    """
        Verifies the token for the user (if provided) in non-production environment. If in production environment,
        checks that the user is in the list of authorized admins

        Args:
            token: Optional[str]

        Returns:
            token: str
   """

    print('=== verify_token_admin ===')
    print('_is_production()', _is_production())


    # If this is production, check that the user is in the list of admins
    if _is_production():
        uid = _get_request_uid()

        print('verify_token_admin uid', uid)

        if uid is not None and uid in app.config['ADMIN_UIDS']:
            return verify_token()

    # If we're not in production, just use the normal verify_token method
    else:
        return verify_token(token)


def get_current_user():
    return UserModelSchema().dump(g.user)


def login(
    uid=None,
    redirect_url=None,
):
    """
        In non-production environment, provides an endpoint for end-to-end system testing that allows the system
        to simulate logging in as a specific user. In production environment, simply logs user in via single-sign-on
        (SSO) Shibboleth authentication headers.

        Args:
            uid:  Optional[str]
            redirect_url: Optional[str]

        Returns:
            str.  If not on production, returns the frontend auth callback URL, with auth token appended.
            If on production and user is authenticated via SSO, returns the frontend auth callback URL,
            with auth token appended.

        Raises:
            ApiError.  If on production and user is not authenticated, returns a 404 error.
   """

    # ----------------------------------------
    # Shibboleth Authentication Headers
    # ----------------------------------------
    # X-Remote-Cn: Daniel Harold Funk (dhf8r)
    # X-Remote-Sn: Funk
    # X-Remote-Givenname: Daniel
    # X-Remote-Uid: dhf8r
    # Eppn: dhf8r@virginia.edu
    # Cn: Daniel Harold Funk (dhf8r)
    # Sn: Funk
    # Givenname: Daniel
    # Uid: dhf8r
    # X-Remote-User: dhf8r@virginia.edu
    # X-Forwarded-For: 128.143.0.10
    # X-Forwarded-Host: dev.crconnect.uvadcos.io
    # X-Forwarded-Server: dev.crconnect.uvadcos.io
    # Connection: Keep-Alive

    print('=== login ===')
    print('_is_production()', _is_production())

    # If we're in production, override any uid with the uid from the SSO request headers
    if _is_production():
        uid = _get_request_uid()

    if uid:
        app.logger.info("SSO_LOGIN: Full URL: " + request.url)
        app.logger.info("SSO_LOGIN: User Id: " + uid)
        app.logger.info("SSO_LOGIN: Will try to redirect to : " + str(redirect_url))

        ldap_info = LdapService().user_info(uid)

        if ldap_info:
            return _handle_login(ldap_info, redirect_url)

    raise ApiError('404', 'unknown')


@app.route('/sso')
def sso():
    response = ""
    response += "<h1>Headers</h1>"
    response += "<ul>"
    for k, v in request.headers:
        response += "<li><b>%s</b> %s</li>\n" % (k, v)
    response += "<h1>Environment</h1>"
    for k, v in request.environ:
        response += "<li><b>%s</b> %s</li>\n" % (k, v)
    return response


def _handle_login(user_info: LdapUserInfo, redirect_url=None):
    """
        On successful login, adds user to database if the user is not already in the system,
        then returns the frontend auth callback URL, with auth token appended.

        Args:
            user_info - an ldap user_info object.
            redirect_url: Optional[str]

        Returns:
            Response.  302 - Redirects to the frontend auth callback URL, with auth token appended.
   """
    print('=== _handle_login ===')
    print('user_info', user_info)
    user = db.session.query(UserModel).filter(UserModel.uid == user_info.uid).first()

    if user is None:
        # Add new user
        user = UserModel()

    user.uid = user_info.uid
    user.display_name = user_info.display_name
    user.email_address = user_info.email_address
    user.affiliation = user_info.affiliation
    user.title = user_info.title

    db.session.add(user)
    db.session.commit()

    # Return the frontend auth callback URL, with auth token appended.
    auth_token = user.encode_auth_token().decode()
    if redirect_url is not None:
        if redirect_url.find("http://") != 0 and redirect_url.find("https://") != 0:
            redirect_url = "http://" + redirect_url
        url = '%s?token=%s' % (redirect_url, auth_token)
        app.logger.info("SSO_LOGIN: REDIRECTING TO: " + url)
        return flask.redirect(url, code=302)
    else:
        app.logger.info("SSO_LOGIN:  NO REDIRECT, JUST RETURNING AUTH TOKEN.")
        return auth_token


def _get_request_uid(uid=None):
    if _is_production():
        uid = request.headers.get("Uid")
        if not uid:
            uid = request.headers.get("X-Remote-Uid")

        if not uid:
            raise ApiError("invalid_sso_credentials", "'Uid' nor 'X-Remote-Uid' were present in the headers: %s"
                           % str(request.headers))

    return uid


def _is_production():
    return 'PRODUCTION' in app.config and app.config['PRODUCTION']
