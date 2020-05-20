import os

from crc import app
from ldap3 import Connection, Server, MOCK_SYNC

from crc.api.common import ApiError


class LdapUserInfo(object):

    def __init__(self, entry):
        self.display_name = entry.displayName.value
        self.given_name = ", ".join(entry.givenName)
        self.email = entry.mail.value
        self.telephone_number = ", ".join(entry.telephoneNumber)
        self.title = ", ".join(entry.title)
        self.department = ", ".join(entry.uvaDisplayDepartment)
        self.affiliation = ", ".join(entry.uvaPersonIAMAffiliation)
        self.sponsor_type = ", ".join(entry.uvaPersonSponsoredType)
        self.uid = entry.uid.value


class LdapService(object):
    search_base = "ou=People,o=University of Virginia,c=US"
    attributes = ['uid', 'cn', 'displayName', 'givenName', 'mail', 'objectClass', 'UvaDisplayDepartment',
                  'telephoneNumber', 'title', 'uvaPersonIAMAffiliation', 'uvaPersonSponsoredType']
    uid_search_string = "(&(objectclass=person)(uid=%s))"

    def __init__(self):
        if app.config['TESTING']:
            server = Server('my_fake_server')
            self.conn = Connection(server, client_strategy=MOCK_SYNC)
            file_path = os.path.abspath(os.path.join(app.root_path, '..', 'tests', 'data', 'ldap_response.json'))
            self.conn.strategy.entries_from_json(file_path)
            self.conn.bind()
        else:
            server = Server(app.config['LDAP_URL'], connect_timeout=app.config['LDAP_TIMEOUT_SEC'])
            self.conn = Connection(server,
                                   auto_bind=True,
                                   receive_timeout=app.config['LDAP_TIMEOUT_SEC'],
                                   )

    def __del__(self):
        if self.conn:
            self.conn.unbind()

    def user_info(self, uva_uid):
        search_string = LdapService.uid_search_string % uva_uid
        self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
        if len(self.conn.entries) < 1:
            raise ApiError("missing_ldap_record", "Unable to locate a user with id %s in LDAP" % uva_uid)
        entry = self.conn.entries[0]
        return(LdapUserInfo(entry))

    def search_users(self, query, limit):
        search_string = LdapService.uid_search_string % query
        self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)

        # Entries are returned as a generator, accessing entries
        # can make subsequent calls to the ldap service, so limit
        # those here.
        count = 0
        results = []
        for entry in self.conn.entries:
            if count > limit:
                break
            results.append(LdapUserInfo(entry))
            count += 1
        return results
