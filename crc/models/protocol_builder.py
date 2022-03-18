import enum

from marshmallow import INCLUDE, post_load, fields

from crc import ma


class ProtocolBuilderInvestigatorType(enum.Enum):
    PI = "Primary Investigator"
    SI = "Sub Investigator"
    DC = "Department Contact"
    SC_I = "Study Coordinator 1"
    SC_II = "Study Coordinator 2"
    AS_C = "Additional Study Coordinators"
    DEPT_CH = "Department Chair"
    IRBC = "IRB Coordinator"
    SCI = "Scientific Contact"


# Deprecated: Marked for removal
class ProtocolBuilderStatus(enum.Enum):
    # • Active: found in PB and not hold
    # • Hold: store boolean value in CR Connect (add to Study Model)
    # • Open To Enrollment: has start date?
    # • Abandoned: deleted in PB
    incomplete = 'incomplete'  # Found in PB but not ready to start (not q_complete)
    active = 'active'  # found in PB, marked as "q_complete" and not hold
    hold = 'hold'  # CR Connect side, if the Study ias marked as "hold".
    open = 'open'  # Open To Enrollment: has start date?
    abandoned = 'abandoned'  # Not found in PB

    # DRAFT = 'draft',                      # !Q_COMPLETE
    # IN_PROCESS = 'in_process',            # Q_COMPLETE && !UPLOAD_COMPLETE
    # IN_REVIEW = 'in_review',              # Q_COMPLETE && (!UPLOAD_COMPLETE)
    # REVIEW_COMPLETE = 'review_complete',  # Q_COMPLETE && UPLOAD_COMPLETE
    # INACTIVE = 'inactive',                # Not found in PB


class ProtocolBuilderCreatorStudy(object):

    def __init__(self, STUDYID, TITLE, REVIEW_TYPE, DATECREATED, DATELASTMODIFIED=None):
        self.STUDYID = STUDYID
        self.DATELASTMODIFIED = DATELASTMODIFIED
        self.DATECREATED = DATECREATED
        self.TITLE = TITLE
        self.REVIEW_TYPE = REVIEW_TYPE

class ProtocolBuilderCreatorStudySchema(ma.Schema):
    class Meta:
        unknown = INCLUDE
    STUDYID = fields.Integer()
    DATELASTMODIFIED = fields.String(allow_none=True)
    DATECREATED = fields.String()
    TITLE = fields.String()
    REVIEW_TYPE = fields.Integer(allow_none=True)

    @post_load
    def make_study(self, data, **kwargs):
        return ProtocolBuilderCreatorStudy(**data)


class ProtocolBuilderInvestigator(object):
    def __init__(self, NETBADGEID: str, INVESTIGATORTYPE: str, INVESTIGATORTYPEFULL: str):
        self.NETBADGEID = NETBADGEID
        self.INVESTIGATORTYPE = INVESTIGATORTYPE
        self.INVESTIGATORTYPEFULL = INVESTIGATORTYPEFULL


class ProtocolBuilderInvestigatorSchema(ma.Schema):
    class Meta:
        model = ProtocolBuilderInvestigator
        unknown = INCLUDE
        fields = ["NETBADGEID", "INVESTIGATORTYPE", "INVESTIGATORTYPEFULL"]

    @post_load
    def make_inv(self, data, **kwargs):
        return ProtocolBuilderInvestigator(**data)


class ProtocolBuilderRequiredDocument(object):
    def __init__(self, AUXDOCID: str, AUXDOC: str):
        self.AUXDOCID = AUXDOCID
        self.AUXDOC = AUXDOC


class ProtocolBuilderRequiredDocumentSchema(ma.Schema):
    class Meta:
        fields = ["AUXDOCID", "AUXDOC"]
        unknown = INCLUDE

    @post_load
    def make_req(self, data, **kwargs):
        return ProtocolBuilderRequiredDocument(**data)
