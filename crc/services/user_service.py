from flask import g

from crc.api.common import ApiError


class UserService(object):
    """Provides common tools for working with users"""

    @staticmethod
    def has_user():
        if 'user' not in g or not g.user:
            return False
        else:
            return True

    @staticmethod
    def current_user(allow_admin_impersonate=False):

        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        # Admins can pretend to be different users and act on a users behalf in
        # some circumstances.
        if g.user.is_admin() and allow_admin_impersonate and "impersonate_user" in g:
            return g.impersonate_user
        else:
            return g.user

    @staticmethod
    def in_list(uids, allow_admin_impersonate=False):
        """Returns true if the current user's id is in the given list of ids.  False if there
        is no user, or the user is not in the list."""
        if UserService.has_user():  # If someone is logged in, lock tasks that don't belong to them.
            user = UserService.current_user(allow_admin_impersonate)
            if user.uid in uids:
                return True
        return False
