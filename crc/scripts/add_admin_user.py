from crc import app, db
from crc.api.common import ApiError
from crc.models.study import StudyAssociated
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService

from sqlalchemy import text


class AddAdminUser(Script):
    scripts = {}

    def get_description(self):
        return """Add a user to the study_associated_user table (for all studies)"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        associated_user = kwargs.get('associated_user', None)
        associated_group = kwargs.get('associated_group', None)
        scripts = self.generate_augmented_list(task, study_id, workflow_id)
        self.scripts = scripts
        try:
            ldap_user = self.scripts['ldap'](associated_user)
        except ApiError as ae:
            return {"error": str(ae), 'message': f"User {associated_user} not found in LDAP"}

        if 'uid' in ldap_user and ldap_user['uid'] == associated_user:
            # study_associated = StudyAssociated()

            # using 'lje5u' because they are in both CTO and CTO Finance groups
            # sql_string = f"select study_id, '{associated_user}', 'CTO', false, true from study_associated_user where uid='lje5u' and role='{associated_group}'"

            sql_string = """insert into study_associated_user
            (study_id, uid, role, send_email, access)
            select study_id, '%s', 'CTO', false, true 
            from study_associated_user 
            where uid='lje5u' and role='%s'""" % (associated_user, associated_group)

            sql = text(sql_string)
            result = db.engine.execute(sql)
            print(result.rowcount)
            return {"message": f"User {associated_user} added to {associated_group} group"}
