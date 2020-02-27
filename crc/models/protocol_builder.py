import enum

from marshmallow import INCLUDE

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
    out_of_date = "out_of_date"
    in_process = "in_process"
    complete = "complete"
    updating = "updating"


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


class ProtocolBuilderInvestigator(object):
    def __init__(self, STUDYID: int, NETBADGEID: str, INVESTIGATORTYPE: str, INVESTIGATORTYPEFULL: str):
        self.STUDYID = STUDYID
        self.NETBADGEID = NETBADGEID
        self.INVESTIGATORTYPE = INVESTIGATORTYPE
        self.INVESTIGATORTYPEFULL = INVESTIGATORTYPEFULL


class ProtocolBuilderInvestigatorSchema(ma.Schema):
    class Meta:
        model = ProtocolBuilderInvestigator
        unknown = INCLUDE


class ProtocolBuilderRequiredDocument(object):
    DOC_TYPES = {
        1: "Investigators Brochure",
        6: "Cancer Center's PRC Approval Form",
        8: "SOM CTO IND/IDE Review Letter",
        9: "HIRE Approval",
        10: "Cancer Center's PRC Approval Waiver",
        12: "Certificate of Confidentiality Application",
        14: "Institutional Biosafety Committee Approval",
        18: "SOM CTO Approval Letter - UVA PI Multisite Trial",
        20: "IRB Approval or Letter of Approval from Administration: Study Conducted at non- UVA Facilities ",
        21: "New Medical Device Form",
        22: "SOM CTO Review regarding need for IDE",
        23: "SOM CTO Review regarding need for IND",
        24: "InfoSec Approval",
        25: "Scientific Pre-review Documentation",
        26: "IBC Number",
        32: "IDS - Investigational Drug Service Approval",
        36: "RDRC Approval ",
        40: "SBS/IRB Approval-FERPA",
        41: "HIRE Standard Radiation Language",
        42: "COI Management Plan ",
        43: "SOM CTO Approval Letter-Non UVA, Non Industry PI MultiSite Study",
        44: "GRIME Approval",
        45: "GMEC Approval",
        46: "IRB Reliance Agreement Request Form- IRB-HSR is IRB of Record",
        47: "Non UVA IRB Approval - Initial and Last Continuation",
        48: "MR Physicist Approval- Use of Gadolinium",
        49: "SOM CTO Approval- Non- UVA Academia PI of IDE",
        51: "IDS Waiver",
        52: "Package Inserts",
        53: "IRB Reliance Agreement Request Form- IRB-HSR Not IRB of Record",
        54: "ESCRO Approval",
        57: "Laser Safety Officer Approval",
    }

    def __init__(self, AUXDOCID: str, AUXDOC: str):
        self.AUXDOCID = AUXDOCID
        self.AUXDOC = AUXDOC


class ProtocolBuilderRequiredDocumentSchema(ma.Schema):
    class Meta:
        model = ProtocolBuilderRequiredDocument
        unknown = INCLUDE


class ProtocolBuilderStudyDetails(object):

    def __init__(
            self,
            STUDYID: int,
            IS_IND: int,
            IND_1: str,
            IND_2: str,
            IND_3: str,
            IS_UVA_IND: int,
            IS_IDE: int,
            IS_UVA_IDE: int,
            IDE: str,
            IS_CHART_REVIEW: int,
            IS_RADIATION: int,
            GCRC_NUMBER: str,
            IS_GCRC: int,
            IS_PRC_DSMP: int,
            IS_PRC: int,
            PRC_NUMBER: str,
            IS_IBC: int,
            IBC_NUMBER: str,
            SPONSORS_PROTOCOL_REVISION_DATE: int,
            IS_SPONSOR_MONITORING: int,
            IS_AUX: int,
            IS_SPONSOR: int,
            IS_GRANT: int,
            IS_COMMITTEE_CONFLICT: int,
            DSMB: int,
            DSMB_FREQUENCY: int,
            IS_DB: int,
            IS_UVA_DB: int,
            IS_CENTRAL_REG_DB: int,
            IS_CONSENT_WAIVER: int,
            IS_HGT: int,
            IS_GENE_TRANSFER: int,
            IS_TISSUE_BANKING: int,
            IS_SURROGATE_CONSENT: int,
            IS_ADULT_PARTICIPANT: int,
            IS_MINOR_PARTICIPANT: int,
            IS_MINOR: int,
            IS_BIOMEDICAL: int,
            IS_QUALITATIVE: int,
            IS_PI_SCHOOL: int,
            IS_PRISONERS_POP: int,
            IS_PREGNANT_POP: int,
            IS_FETUS_POP: int,
            IS_MENTAL_IMPAIRMENT_POP: int,
            IS_ELDERLY_POP: int,
            IS_OTHER_VULNERABLE_POP: int,
            OTHER_VULNERABLE_DESC: str,
            IS_MULTI_SITE: int,
            IS_UVA_LOCATION: int,
            NON_UVA_LOCATION: str,
            MULTI_SITE_LOCATIONS: str,
            IS_OUTSIDE_CONTRACT: int,
            IS_UVA_PI_MULTI: int,
            IS_NOT_PRC_WAIVER: int,
            IS_CANCER_PATIENT: int,
            UPLOAD_COMPLETE: int,
            IS_FUNDING_SOURCE: int,
            IS_PI_INITIATED: int,
            IS_ENGAGED_RESEARCH: int,
            IS_APPROVED_DEVICE: int,
            IS_FINANCIAL_CONFLICT: int,
            IS_NOT_CONSENT_WAIVER: int,
            IS_FOR_CANCER_CENTER: int,
            IS_REVIEW_BY_CENTRAL_IRB: int,
            IRBREVIEWERADMIN: str
    ):
        self.STUDYID = STUDYID
        self.IS_IND = IS_IND
        self.IND_1 = IND_1
        self.IND_2 = IND_2
        self.IND_3 = IND_3
        self.IS_UVA_IND = IS_UVA_IND
        self.IS_IDE = IS_IDE
        self.IS_UVA_IDE = IS_UVA_IDE
        self.IDE = IDE
        self.IS_CHART_REVIEW = IS_CHART_REVIEW
        self.IS_RADIATION = IS_RADIATION
        self.GCRC_NUMBER = GCRC_NUMBER
        self.IS_GCRC = IS_GCRC
        self.IS_PRC_DSMP = IS_PRC_DSMP
        self.IS_PRC = IS_PRC
        self.PRC_NUMBER = PRC_NUMBER
        self.IS_IBC = IS_IBC
        self.IBC_NUMBER = IBC_NUMBER
        self.SPONSORS_PROTOCOL_REVISION_DATE = SPONSORS_PROTOCOL_REVISION_DATE
        self.IS_SPONSOR_MONITORING = IS_SPONSOR_MONITORING
        self.IS_AUX = IS_AUX
        self.IS_SPONSOR = IS_SPONSOR
        self.IS_GRANT = IS_GRANT
        self.IS_COMMITTEE_CONFLICT = IS_COMMITTEE_CONFLICT
        self.DSMB = DSMB
        self.DSMB_FREQUENCY = DSMB_FREQUENCY
        self.IS_DB = IS_DB
        self.IS_UVA_DB = IS_UVA_DB
        self.IS_CENTRAL_REG_DB = IS_CENTRAL_REG_DB
        self.IS_CONSENT_WAIVER = IS_CONSENT_WAIVER
        self.IS_HGT = IS_HGT
        self.IS_GENE_TRANSFER = IS_GENE_TRANSFER
        self.IS_TISSUE_BANKING = IS_TISSUE_BANKING
        self.IS_SURROGATE_CONSENT = IS_SURROGATE_CONSENT
        self.IS_ADULT_PARTICIPANT = IS_ADULT_PARTICIPANT
        self.IS_MINOR_PARTICIPANT = IS_MINOR_PARTICIPANT
        self.IS_MINOR = IS_MINOR
        self.IS_BIOMEDICAL = IS_BIOMEDICAL
        self.IS_QUALITATIVE = IS_QUALITATIVE
        self.IS_PI_SCHOOL = IS_PI_SCHOOL
        self.IS_PRISONERS_POP = IS_PRISONERS_POP
        self.IS_PREGNANT_POP = IS_PREGNANT_POP
        self.IS_FETUS_POP = IS_FETUS_POP
        self.IS_MENTAL_IMPAIRMENT_POP = IS_MENTAL_IMPAIRMENT_POP
        self.IS_ELDERLY_POP = IS_ELDERLY_POP
        self.IS_OTHER_VULNERABLE_POP = IS_OTHER_VULNERABLE_POP
        self.OTHER_VULNERABLE_DESC = OTHER_VULNERABLE_DESC
        self.IS_MULTI_SITE = IS_MULTI_SITE
        self.IS_UVA_LOCATION = IS_UVA_LOCATION
        self.NON_UVA_LOCATION = NON_UVA_LOCATION
        self.MULTI_SITE_LOCATIONS = MULTI_SITE_LOCATIONS
        self.IS_OUTSIDE_CONTRACT = IS_OUTSIDE_CONTRACT
        self.IS_UVA_PI_MULTI = IS_UVA_PI_MULTI
        self.IS_NOT_PRC_WAIVER = IS_NOT_PRC_WAIVER
        self.IS_CANCER_PATIENT = IS_CANCER_PATIENT
        self.UPLOAD_COMPLETE = UPLOAD_COMPLETE
        self.IS_FUNDING_SOURCE = IS_FUNDING_SOURCE
        self.IS_PI_INITIATED = IS_PI_INITIATED
        self.IS_ENGAGED_RESEARCH = IS_ENGAGED_RESEARCH
        self.IS_APPROVED_DEVICE = IS_APPROVED_DEVICE
        self.IS_FINANCIAL_CONFLICT = IS_FINANCIAL_CONFLICT
        self.IS_NOT_CONSENT_WAIVER = IS_NOT_CONSENT_WAIVER
        self.IS_FOR_CANCER_CENTER = IS_FOR_CANCER_CENTER
        self.IS_REVIEW_BY_CENTRAL_IRB = IS_REVIEW_BY_CENTRAL_IRB
        self.IRBREVIEWERADMIN = IRBREVIEWERADMIN


class ProtocolBuilderStudyDetailsSchema(ma.Schema):
    class Meta:
        model = ProtocolBuilderStudyDetails
        unknown = INCLUDE
