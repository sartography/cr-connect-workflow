from crc import app
from ldap3 import Connection, Server

from crc.api.common import ApiError


class LdapUserInfo(object):

    def __init__(self, entry):
        self.display_name = entry.displayName.value
        self.given_name = ", ".join(entry.givenName)
        self.email = entry.mail.value
        self.telephone_number= ", ".join(entry.telephoneNumber)
        self.title = ", ".join(entry.title)
        self.department = ", ".join(entry.uvaDisplayDepartment)
        self.affiliation = ", ".join(entry.uvaPersonIAMAffiliation)
        self.sponsor_type = ", ".join(entry.uvaPersonSponsoredType)




class LdapService(object):
    search_base = "ou=People,o=University of Virginia,c=US"
    attributes = ['cn', 'displayName', 'givenName', 'mail', 'objectClass', 'UvaDisplayDepartment',
                  'telephoneNumber', 'title', 'uvaPersonIAMAffiliation', 'uvaPersonSponsoredType']
    search_string = "(&(objectclass=person)(uid=%s))"

    def __init__(self, connection=None):
        self.conn = None
        if connection is None:
            server = Server(app.config['LDAP_URL'], connect_timeout=app.config['LDAP_TIMEOUT_SEC'])
            self.conn = Connection(server,
                                   auto_bind=True,
                                   receive_timeout=app.config['LDAP_TIMEOUT_SEC'],
                                   )
        else:
            self.conn = connection

    def __del__(self):
        if self.conn:
            self.conn.unbind()

    def user_info(self, uva_uid):
        search_string = LdapService.search_string % uva_uid
        self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
        if len(self.conn.entries) < 1:
            raise ApiError("missing_ldap_record", "Unable to locate a user with id %s in LDAP" % uva_uid)
        entry = self.conn.entries[0]
        return(LdapUserInfo(entry))
