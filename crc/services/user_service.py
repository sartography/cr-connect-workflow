from flask import g, session

from crc import db
from crc.api.common import ApiError
from crc.models.user import UserModel


class UserService(object):
    """Provides common tools for working with users"""

    # Returns true if the current user is logged in.
    @staticmethod
    def has_user():
        return 'user' in g and bool(g.user)

    # Returns true if the current user is an admin.
    @staticmethod
    def user_is_admin():
        return UserService.has_user() and g.user.is_admin()

    # Returns true if the current admin user is impersonating another user.
    @staticmethod
    def admin_is_impersonating():
        return UserService.user_is_admin() and \
               "admin_impersonate_uid" in session and \
               session.get('admin_impersonate_uid') is not None

    # Returns true if the given user uid is different from the current user's uid.
    @staticmethod
    def is_different_user(uid):
        return UserService.has_user() and uid is not None and uid is not g.user.uid

    @staticmethod
    def current_user(allow_admin_impersonate=False):
        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        # Admins can pretend to be different users and act on a user's behalf in
        # some circumstances.
        if allow_admin_impersonate and UserService.admin_is_impersonating():
            return g.impersonate_user
        else:
            return g.user

    # Admins can pretend to be different users and act on a user's behalf in some circumstances.
    # This method allows an admin user to start impersonating another user with the given uid.
    # Stops impersonating if the uid is None or invalid.
    @staticmethod
    def impersonate(uid=None):
        # Clear out the current impersonating user.
        g.impersonate_user = None
        session.pop('admin_impersonate_uid', None)

        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        if not UserService.admin_is_impersonating() and UserService.is_different_user(uid):
            # Impersonate the user if the given uid is valid.
            g.impersonate_user = db.session.query(UserModel).filter(UserModel.uid == uid).first()

            # Store the uid in the session.
            if g.impersonate_user:
                session['admin_impersonate_uid'] = uid

    @staticmethod
    def in_list(uids, allow_admin_impersonate=False):
        """Returns true if the current user's id is in the given list of ids.  False if there
        is no user, or the user is not in the list."""
        if UserService.has_user():  # If someone is logged in, lock tasks that don't belong to them.
            user = UserService.current_user(allow_admin_impersonate)
            if user.uid in uids:
                return True
        return False
