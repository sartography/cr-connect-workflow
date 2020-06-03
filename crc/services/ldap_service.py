import os

from attr import asdict
from ldap3.core.exceptions import LDAPExceptionError

from crc import app, db
from ldap3 import Connection, Server, MOCK_SYNC

from crc.api.common import ApiError
from crc.models.ldap import LdapModel, LdapSchema


class LdapService(object):
    search_base = "ou=People,o=University of Virginia,c=US"
    attributes = ['uid', 'cn', 'sn', 'displayName', 'givenName', 'mail', 'objectClass', 'UvaDisplayDepartment',
                  'telephoneNumber', 'title', 'uvaPersonIAMAffiliation', 'uvaPersonSponsoredType']
    uid_search_string = "(&(objectclass=person)(uid=%s))"
    user_or_last_name_search = "(&(objectclass=person)(|(uid=%s*)(sn=%s*)))"
    cn_single_search = '(&(objectclass=person)(cn=%s*))'
    cn_double_search = '(&(objectclass=person)(&(cn=%s*)(cn=*%s*)))'

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
        user_info = db.session.query(LdapModel).filter(LdapModel.uid == uva_uid).first()
        if not user_info:
            search_string = LdapService.uid_search_string % uva_uid
            self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
            if len(self.conn.entries) < 1:
                raise ApiError("missing_ldap_record", "Unable to locate a user with id %s in LDAP" % uva_uid)
            entry = self.conn.entries[0]
            user_info = LdapModel.from_entry(entry)
            db.session.add(user_info)
        return user_info

    def search_users(self, query, limit):
        if len(query.strip()) < 3:
            return []
        elif query.endswith(' '):
            search_string = LdapService.cn_single_search % (query.strip())
        elif query.strip().count(',') == 1:
            f, l = query.split(",")
            search_string = LdapService.cn_double_search % (l.strip(), f.strip())
        elif query.strip().count(' ') == 1:
            f,l = query.split(" ")
            search_string = LdapService.cn_double_search % (f, l)
        else:
            # Search by user_id or last name
            search_string = LdapService.user_or_last_name_search % (query, query)
        results = []
        print(search_string)
        try:
            self.conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
            # Entries are returned as a generator, accessing entries
            # can make subsequent calls to the ldap service, so limit
            # those here.
            count = 0
            for entry in self.conn.entries:
                if count > limit:
                    break
                results.append(LdapSchema().dump(LdapModel.from_entry(entry)))
                count += 1
        except LDAPExceptionError as le:
            app.logger.info("Failed to execute ldap search. %s", str(le))

        return results
