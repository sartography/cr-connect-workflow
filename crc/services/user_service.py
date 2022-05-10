from flask import g

import crc.api.user
from crc import session
from flask_bpmn.api.common import ApiError
from crc.services.ldap_service import LdapService
from crc.models.user import UserModel, AdminSessionModel


class UserService(object):
    """Provides common tools for working with users"""

    # Returns true if the current user is logged in.
    @staticmethod
    def has_user():
        return 'token' in g and \
               bool(g.token) and \
               'user' in g and \
               bool(g.user)

    # Returns true if the current user is an admin.
    @staticmethod
    def user_is_admin():
        return UserService.has_user() and g.user.is_admin()

    # Returns true if the current admin user is impersonating another user.
    @staticmethod
    def admin_is_impersonating():
        if UserService.user_is_admin():
            adminSession: AdminSessionModel = UserService.get_admin_session()
            return adminSession is not None

        else:
            raise ApiError("unauthorized", "You do not have permissions to do this.", status_code=403)

    # Returns true if the given user uid is different from the current user's uid.
    @staticmethod
    def is_different_user(uid):
        return UserService.has_user() and uid is not None and uid is not g.user.uid

    @staticmethod
    def current_user(allow_admin_impersonate=False) -> UserModel:
        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        # Admins can pretend to be different users and act on a user's behalf in
        # some circumstances.
        if UserService.user_is_admin() and allow_admin_impersonate and UserService.admin_is_impersonating():
            return UserService.get_admin_session_user()
        else:
            return g.user

    # Admins can pretend to be different users and act on a user's behalf in some circumstances.
    # This method allows an admin user to start impersonating another user with the given uid.
    # Stops impersonating if the uid is None or invalid.
    @staticmethod
    def start_impersonating(uid=None):
        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        if not UserService.user_is_admin():
            raise ApiError("unauthorized", "You do not have permissions to do this.", status_code=403)

        if uid is None:
            raise ApiError("invalid_uid", "Please provide a valid user uid.")

        if UserService.is_different_user(uid):
            # Impersonate the user if the given uid is valid.

            # If the user is not in the User table, add them to it
            ldap_info = LdapService().user_info(uid)
            crc.api.user._upsert_user(ldap_info)

            impersonate_user = session.query(UserModel).filter(UserModel.uid == uid).first()

            if impersonate_user is not None:
                g.impersonate_user = impersonate_user

                # Store the uid and user session token.
                session.query(AdminSessionModel).filter(AdminSessionModel.token==g.token).delete()
                session.add(AdminSessionModel(token=g.token, admin_impersonate_uid=uid))
                session.commit()
            else:
                raise ApiError("invalid_uid", "The uid provided is not valid.")

    @staticmethod
    def stop_impersonating():
        if not UserService.has_user():
            raise ApiError("logged_out", "You are no longer logged in.", status_code=401)

        # Clear out the current impersonating user.
        if 'impersonate_user' in g:
            del g.impersonate_user

        admin_session: AdminSessionModel = UserService.get_admin_session()
        if admin_session:
            session.delete(admin_session)
            session.commit()

    @staticmethod
    def in_list(uids, allow_admin_impersonate=False):
        """Returns true if the current user's id is in the given list of ids.  False if there
        is no user, or the user is not in the list."""
        if UserService.has_user():  # If someone is logged in, lock tasks that don't belong to them.
            user = UserService.current_user(allow_admin_impersonate)
            if user.uid in uids:
                return True
        return False

    @staticmethod
    def get_admin_session() -> AdminSessionModel:
        if UserService.user_is_admin():
            return session.query(AdminSessionModel).filter(AdminSessionModel.token == g.token).first()
        else:
            raise ApiError("unauthorized", "You do not have permissions to do this.", status_code=403)

    @staticmethod
    def get_admin_session_user() -> UserModel:
        if UserService.user_is_admin():
            admin_session = UserService.get_admin_session()

            if admin_session is not None:
                return session.query(UserModel).filter(UserModel.uid == admin_session.admin_impersonate_uid).first()
        else:
            raise ApiError("unauthorized", "You do not have permissions to do this.", status_code=403)
