import connexion
from flask import redirect, g

from crc import sso, app, db
from crc.api.common import ApiError
from crc.models.user import UserModel, UserModelSchema


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


@sso.login_handler
def sso_login(user_info):
    # TODO: Get redirect URL from Shibboleth request header
    _handle_login(user_info)


def _handle_login(user_info, redirect_url=app.config['FRONTEND_AUTH_CALLBACK']):
    """On successful login, adds user to database if the user is not already in the system,
       then returns the frontend auth callback URL, with auth token appended.

       Args:
           user_info (dict of {
                uid: str,
                affiliation: Optional[str],
                display_name: Optional[str],
                email_address: Optional[str],
                eppn: Optional[str],
                first_name: Optional[str],
                last_name: Optional[str],
                title: Optional[str],
           }): Dictionary of user attributes
          redirect_url: Optional[str]

       Returns:
           Response.  302 - Redirects to the frontend auth callback URL, with auth token appended.
   """
    uid = user_info['uid']
    user = db.session.query(UserModel).filter(UserModel.uid == uid).first()

    if user is None:
        # Add new user
        user = UserModelSchema().load(user_info, session=db.session)
    else:
        # Update existing user data
        user = UserModelSchema().load(user_info, session=db.session, instance=user, partial=True)

    # Build display_name if not set
    if 'display_name' not in user_info or len(user_info['display_name']) == 0:
        display_name_list = []

        for prop in ['first_name', 'last_name']:
            if prop in user_info and len(user_info[prop]) > 0:
                display_name_list.append(user_info[prop])

        user.display_name = ' '.join(display_name_list)

    db.session.add(user)
    db.session.commit()

    # Return the frontend auth callback URL, with auth token appended.
    auth_token = user.encode_auth_token().decode()
    if redirect_url is not None:
        return redirect('%s/%s' % (redirect_url, auth_token))
    else:
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
        user_info = {}
        for key in UserModel.__dict__.keys():
            if key in connexion.request.args:
                user_info[key] = connexion.request.args[key]

        return _handle_login(user_info, redirect_url)
    else:
        raise ApiError('404', 'unknown')
