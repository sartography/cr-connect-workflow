import json

import connexion
from flask import redirect, g, request

from crc import app, db
from crc.api.common import ApiError
from crc.models.user import UserModel, UserModelSchema
from crc.services.ldap_service import LdapService, LdapUserInfo

"""
.. module:: crc.api.user
   :synopsis: Single Sign On (SSO) user login and session handlers
"""
def verify_token(token):
    failure_error = ApiError("invalid_token", "Unable to decode the token you provided.  Please re-authenticate", status_code=403)
    if (not 'PRODUCTION' in app.config or not app.config['PRODUCTION']) and token == app.config["SWAGGER_AUTH_KEY"]:
        g.user = UserModel.query.first()
        token = g.user.encode_auth_token()

    try:
        token_info = UserModel.decode_auth_token(token)
        g.user = UserModel.query.filter_by(uid=token_info['sub']).first()
    except:
        raise failure_error
    if g.user is not None:
        return token_info
    else:
        raise failure_error


def get_current_user():
    return UserModelSchema().dump(g.user)

@app.route('/login')
def sso_login():
    # This what I see coming back:
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
    uid = request.headers.get("Uid")
    if not uid:
        uid = request.headers.get("X-Remote-Uid")

    if not uid:
        raise ApiError("invalid_sso_credentials", "'Uid' nor 'X-Remote-Uid' were present in the headers: %s"
                       % str(request.headers))

    redirect = request.args.get('redirect')
    app.logger.info("SSO_LOGIN: Full URL: " + request.url)
    app.logger.info("SSO_LOGIN: User Id: " + uid)
    app.logger.info("SSO_LOGIN: Will try to redirect to : " + str(redirect))

    ldap_service = LdapService()
    info = ldap_service.user_info(uid)

    return _handle_login(info, redirect)

@app.route('/sso')
def sso():
    response = ""
    response += "<h1>Headers</h1>"
    response += "<ul>"
    for k,v in request.headers:
        response += "<li><b>%s</b> %s</li>\n" % (k, v)
    response += "<h1>Environment</h1>"
    for k,v in request.environ:
        response += "<li><b>%s</b> %s</li>\n" % (k, v)
    return response


def _handle_login(user_info: LdapUserInfo, redirect_url=app.config['FRONTEND_AUTH_CALLBACK']):
    """On successful login, adds user to database if the user is not already in the system,
       then returns the frontend auth callback URL, with auth token appended.

       Args:
           user_info - an ldap user_info object.
           redirect_url: Optional[str]

       Returns:
           Response.  302 - Redirects to the frontend auth callback URL, with auth token appended.
   """
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
        app.logger.info("SSO_LOGIN: REDIRECTING TO: " + redirect_url)
        return redirect('%s/%s' % (redirect_url, auth_token))
    else:
        app.logger.info("SSO_LOGIN:  NO REDIRECT, JUST RETURNING AUTH TOKEN.")
        return auth_token



def backdoor(
    uid=None,
    affiliation=None,
    display_name=None,
    email_address=None,
    eppn=None,
    first_name=None,
    last_name=None,
    title=None,
    redirect_url=None,
):
    """A backdoor for end-to-end system testing that allows the system to simulate logging in as a specific user.
       Only works if the application is running in a non-production environment.

       Args:
          uid: str
          affiliation: Optional[str]
          display_name: Optional[str]
          email_address: Optional[str]
          eppn: Optional[str]
          first_name: Optional[str]
          last_name: Optional[str]
          title: Optional[str]
          redirect_url: Optional[str]

       Returns:
           str.  If not on production, returns the frontend auth callback URL, with auth token appended.

       Raises:
           ApiError.  If on production, returns a 404 error.
   """
    if not 'PRODUCTION' in app.config or not app.config['PRODUCTION']:

        ldap_info = LdapService().user_info(uid)
        return _handle_login(ldap_info, redirect_url)
    else:
        raise ApiError('404', 'unknown')
