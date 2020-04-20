from crc import app
from ldap3 import Connection


class LdapUserInfo(object):

    def __init__(self, entry):
        self.display_name = entry.displayName
        self.given_name = ", ".join(entry.givenName)
        self.email = entry.mail
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
        if connection is None:
            self.LDAP_URL = app.config['LDAP_URL']
            self.conn = Connection(self.LDAP_URL, auto_bind=True, client_strategy='SYNC')
        else:
            self.conn = connection

    def __del__(self):
        self.conn.unbind()

    def user_info(self, uva_uid):
        search_string = LdapService.search_string % uva_uid
        self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
        entry = self.conn.entries[0]
        return(LdapUserInfo(entry))
