import os
from ldap3.core.exceptions import LDAPExceptionError
import datetime as dt

from crc import app, db
from ldap3 import Connection, Server, MOCK_SYNC, RESTARTABLE

from flask_bpmn.api.common import ApiError
from crc.models.ldap import LdapModel, LdapSchema


class LdapService(object):
    search_base = "ou=People,o=University of Virginia,c=US"
    attributes = ['uid', 'cn', 'sn', 'displayName', 'givenName', 'mail', 'objectClass', 'UvaDisplayDepartment',
                  'telephoneNumber', 'title', 'uvaPersonIAMAffiliation', 'uvaPersonSponsoredType']
    uid_search_string = "(&(objectclass=person)(uid=%s))"
    user_or_last_name_search = "(&(objectclass=person)(|(uid=%s*)(sn=%s*)))"
    cn_single_search = '(&(objectclass=person)(cn=%s*))'
    cn_double_search = '(&(objectclass=person)(&(cn=%s*)(cn=*%s*)))'
    temp_cache = {}
    conn = None

    @staticmethod
    def __get_conn():
        if not LdapService.conn:
            if app.config['LDAP_URL'] == 'mock':
                server = Server('my_fake_server')
                conn = Connection(server, client_strategy=MOCK_SYNC)
                file_path = os.path.abspath(os.path.join(app.root_path, '..', 'tests', 'data', 'ldap_response.json'))
                conn.strategy.entries_from_json(file_path)
                conn.bind()
            elif "LDAP_USER" in app.config and app.config['LDAP_USER'].strip() != '':
                server = Server(host=app.config['LDAP_URL'], use_ssl=True)
                conn = Connection(server, auto_bind=True,
                                  user=app.config['LDAP_USER'],
                                  password=app.config['LDAP_PASS'],
                                  receive_timeout=app.config['LDAP_TIMEOUT_SEC'],
                                  client_strategy=RESTARTABLE)
            else:
                server = Server(app.config['LDAP_URL'], connect_timeout=app.config['LDAP_TIMEOUT_SEC'])
                conn = Connection(server, auto_bind=True,
                                  receive_timeout=app.config['LDAP_TIMEOUT_SEC'],
                                  client_strategy=RESTARTABLE)
            LdapService.conn = conn
        return LdapService.conn

    @staticmethod
    def user_exists(uva_uid):
        try:
            x = LdapService.user_info(uva_uid)
        except:
            return False
        return True

    @staticmethod
    def user_info(uva_uid):
        uva_uid = uva_uid.strip().lower()
        user_info = db.session.query(LdapModel).filter(LdapModel.uid == uva_uid).first()
        if not user_info:
            app.logger.info("No cache for " + uva_uid)
            search_string = LdapService.uid_search_string % uva_uid
            conn = LdapService.__get_conn()
            conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
            if len(conn.entries) < 1:
                raise ApiError("missing_ldap_record", "Unable to locate a user with id %s in LDAP" % uva_uid)
            entry = conn.entries[0]
            # Assure it definitely doesn't exist in the db after a search, in some cases the ldap server
            # may find stuff we don't with just a strip and a lower.
            user_info = db.session.query(LdapModel).filter(LdapModel.uid == entry.uid.value).first()
            if not user_info:
                user_info = LdapModel.from_entry(entry)
                db.session.add(user_info)
                db.session.commit()
        return user_info

    @staticmethod
    def search_users(query, limit):
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
        try:
            conn = LdapService.__get_conn()
            a = dt.datetime.now()
            conn.search(LdapService.search_base, search_string, attributes=LdapService.attributes)
            b = dt.datetime.now()
            app.logger.info('LDAP Search ' + search_string + " -- " + str((b - a).total_seconds()) + " sec.")

            # Entries are returned as a generator, accessing entries
            # can make subsequent calls to the ldap service, so limit
            # those here.
            count = 0
            for entry in conn.entries:
                if count > limit:
                    break
                results.append(LdapSchema().dump(LdapModel.from_entry(entry)))
                count += 1
        except LDAPExceptionError as le:
            app.logger.info("Failed to execute ldap search. %s", str(le))

        return results
