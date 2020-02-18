from flask import redirect, g

from crc import sso, app, db, auth
from crc.api.common import ApiError


# User Accounts
# *****************************
from crc.models.user import UserModel, UserModelSchema


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
    uid = user_info['uid']
    user = db.session.query(UserModel).filter(UserModel.uid == uid).first()
    if user is None:
        user = UserModel(uid=uid,
                         display_name=user_info["givenName"],
                         email_address=user_info["email"])
        if "Surname" in user_info:
            user.display_name = user.display_name + " " + user_info["Surname"]

        if "displayName" in user_info and len(user_info["displayName"]) > 1:
            user.display_name = user_info["displayName"]

        db.session.add(user)
        db.session.commit()
    # redirect users back to the front end, include the new auth token.
    auth_token = user.encode_auth_token().decode()
    response_url = ("%s/%s" % (app.config["FRONTEND_AUTH_CALLBACK"], auth_token))
    return redirect(response_url)


def backdoor(uid):
    '''A backdoor that allows someone to log in as a specific user, if they
       are in a staging environment. '''
    if not "PRODUCTION" in app.config or not app.config["PRODUCTION"]:
        user_info = {
            "uid": uid,
            "givenName": uid,
            "email": uid + "@virginia.edu"
        }
        return _handle_login(user_info)
    else:
        raise ApiError("404", "unknown")

