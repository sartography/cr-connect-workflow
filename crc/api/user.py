import connexion
from flask import redirect, g

from crc import sso, app, db, auth
from crc.api.common import ApiError
from crc.models.user import UserModel, UserModelSchema

"""
.. module:: crc.api.user
   :synopsis: Single Sign On (SSO) user login and session handlers
"""


@auth.verify_token
def verify_token(token):
    try:
        resp = UserModel.decode_auth_token(token)
        g.user = UserModel.query.filter_by(uid=resp).first()
    except:
        return False

    if g.user is not None:
        return True
    else:
        return False


@auth.login_required
def get_current_user():
    return UserModelSchema().dump(g.user)


@sso.login_handler
def sso_login(user_info):
    _handle_login(user_info)


def _handle_login(user_info):
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

       Returns:
           str.  returns the frontend auth callback URL, with auth token appended.
   """
    uid = user_info['uid']
    user = db.session.query(UserModel).filter(UserModel.uid == uid).first()

    if user is not None:
        del user_info['uid']  # Prevents duplicate uid errors

    # Update existing user data or create a new user
    user = UserModelSchema().load(user_info, session=db.session)

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
    response_url = ('%s/%s' % (app.config['FRONTEND_AUTH_CALLBACK'], auth_token))
    return redirect(response_url)


def backdoor():
    """A backdoor for end-to-end system testing that allows the system to simulate logging in as a specific user.
       Only works if the application is running in a non-production environment.

       Args:
           headers (dict of {
                uid: str,
                affiliation: Optional[str],
                display_name: Optional[str],
                email_address: Optional[str],
                eppn: Optional[str],
                first_name: Optional[str],
                last_name: Optional[str],
                title: Optional[str],
           }): Dictionary of user attributes

       Returns:
           str.  If not on production, returns the frontend auth callback URL, with auth token appended.

       Raises:
           ApiError.  If on production, returns a 404 error.
   """
    if not 'PRODUCTION' in app.config or not app.config['PRODUCTION']:
        # Translate uppercase HTTP_PROP_NAME to lowercase without HTTP_, if property exists in UserModel.
        user_info = {}
        for key, value in connexion.request.environ.items():
            if key.startswith('HTTP_'):
                prop = key[5:].lower()
                if hasattr(UserModel, prop):
                    user_info[prop] = value

        return _handle_login(user_info)
    else:
        raise ApiError('404', 'unknown')
