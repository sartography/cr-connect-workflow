import os

from crc import app
from ldap3 import Connection, Server, MOCK_SYNC

from crc.api.common import ApiError


class LdapUserInfo(object):

    def __init__(self):
        self.display_name = ''
        self.given_name = ''
        self.email_address = ''
        self.telephone_number = ''
        self.title = ''
        self.department = ''
        self.affiliation = ''
        self.sponsor_type = ''
        self.uid = ''

    @classmethod
    def from_entry(cls, entry):
        instance = cls()
        instance.display_name = entry.displayName.value
        instance.given_name = ", ".join(entry.givenName)
        instance.email_address = entry.mail.value
        instance.telephone_number = ", ".join(entry.telephoneNumber)
        instance.title = ", ".join(entry.title)
        instance.department = ", ".join(entry.uvaDisplayDepartment)
        instance.affiliation = ", ".join(entry.uvaPersonIAMAffiliation)
        instance.sponsor_type = ", ".join(entry.uvaPersonSponsoredType)
        instance.uid = entry.uid.value
        return instance

class LdapService(object):
    search_base = "ou=People,o=University of Virginia,c=US"
    attributes = ['uid', 'cn', 'sn', 'displayName', 'givenName', 'mail', 'objectClass', 'UvaDisplayDepartment',
                  'telephoneNumber', 'title', 'uvaPersonIAMAffiliation', 'uvaPersonSponsoredType']
    uid_search_string = "(&(objectclass=person)(uid=%s))"
    user_or_last_name_search_string = "(&(objectclass=person)(|(uid=%s*)(sn=%s*)))"

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
        return LdapUserInfo.from_entry(entry)

    def search_users(self, query, limit):
        if len(query) < 3: return []
        search_string = LdapService.user_or_last_name_search_string % (query, query)
        self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)

        # Entries are returned as a generator, accessing entries
        # can make subsequent calls to the ldap service, so limit
        # those here.
        count = 0
        results = []
        for entry in self.conn.entries:
            if count > limit:
                break
            results.append(LdapUserInfo.from_entry(entry))
            count += 1
        return results
