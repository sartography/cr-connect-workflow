import enum

from marshmallow import INCLUDE, post_load

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


class ProtocolBuilderStatus(enum.Enum):
    # • Active: found in PB and no HSR number and not hold
    # • Hold: store boolean value in CR Connect (add to Study Model)
    # • Open To Enrollment: has start date and HSR number?
    # • Abandoned: deleted in PB
    INCOMPLETE = 'incomplete' # Found in PB but not ready to start (not q_complete)
    ACTIVE = 'active', # found in PB, marked as "q_complete" and no HSR number and not hold
    HOLD = 'hold', # CR Connect side, if the Study ias marked as "hold".
    OPEN = 'open', # Open To Enrollment: has start date and HSR number?
    ABANDONED = 'Abandoned'  # Not found in PB


    #DRAFT = 'draft',                      # !Q_COMPLETE
    #IN_PROCESS = 'in_process',            # Q_COMPLETE && !UPLOAD_COMPLETE && !HSRNUMBER
    #IN_REVIEW = 'in_review',              # Q_COMPLETE && (!UPLOAD_COMPLETE || !HSRNUMBER)
    #REVIEW_COMPLETE = 'review_complete',  # Q_COMPLETE && UPLOAD_COMPLETE && HSRNUMBER
    #INACTIVE = 'inactive',                # Not found in PB



class ProtocolBuilderStudy(object):
    def __init__(
            self, STUDYID: int, HSRNUMBER: str, TITLE: str, NETBADGEID: str,
            Q_COMPLETE: bool, DATE_MODIFIED: str
    ):
        self.STUDYID = STUDYID
        self.HSRNUMBER = HSRNUMBER
        self.TITLE = TITLE
        self.NETBADGEID = NETBADGEID
        self.Q_COMPLETE = Q_COMPLETE
        self.DATE_MODIFIED = DATE_MODIFIED


class ProtocolBuilderStudySchema(ma.Schema):
    class Meta:
        model = ProtocolBuilderStudy
        unknown = INCLUDE
        fields = ["STUDYID", "HSRNUMBER", "TITLE", "NETBADGEID",
                  "Q_COMPLETE", "DATE_MODIFIED"]

    @post_load
    def make_pbs(self, data, **kwargs):
        return ProtocolBuilderStudy(**data)


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
        fields = ["AUXDOCID","AUXDOC"]
        unknown = INCLUDE

    @post_load
    def make_req(self, data, **kwargs):
        return ProtocolBuilderRequiredDocument(**data)
