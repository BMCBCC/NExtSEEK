# backend/app/models/schemas.py

from pydantic import BaseModel
from typing import Optional, Any

class NHPInfo(BaseModel):
    UID: Optional[Any] = None
    Name: Optional[Any] = None
    ID: Optional[Any] = None
    DateOfBirth: Optional[Any] = None
    Sex: Optional[Any] = None
    Species: Optional[Any] = None
    Origin: Optional[Any] = None
    Facility: Optional[Any] = None
    Notes: Optional[Any] = None
    Contact: Optional[Any] = None
    Scientist: Optional[Any] = None
    Publish_uri: Optional[Any] = None
    CoScientist: Optional[Any] = None
    Treatment1: Optional[Any] = None
    Treatment1Type: Optional[Any] = None
    Treatment1Route: Optional[Any] = None
    Treatment1Date: Optional[Any] = None
    Treatment1Dose: Optional[Any] = None
    Treatment1DoseUnits: Optional[Any] = None
    Treatment2: Optional[Any] = None
    Treatment2Type: Optional[Any] = None
    Treatment2Route: Optional[Any] = None
    Treatment2Date: Optional[Any] = None
    Treatment2Dose: Optional[Any] = None
    Treatment2DoseUnits: Optional[Any] = None
    NecropsyDate: Optional[Any] = None
    Cohort: Optional[Any] = None
    Supplier: Optional[Any] = None
    Treatment3: Optional[Any] = None
    Treatment3Type: Optional[Any]
    Protocol: Optional[Any] = None
    Study: Optional[Any] = None
    Funder: Optional[Any] = None
    TotalCFU: Optional[Any] = None
    LungCFU: Optional[Any] = None
    LymphNodeCFU: Optional[Any] = None
    TotalPathologyScore: Optional[Any] = None
    LungPathologyScore: Optional[Any] = None
    LymphNodePathologyScore: Optional[Any] = None
    CFUUnits: Optional[Any] = None
    AlternativeID: Optional[Any] = None
    StudyDesign: Optional[Any] = None
    Link_StudyDesign: Optional[Any] = None
    NewGranulomaCount: Optional[Any] = None

class TimelineEvent(BaseModel):
    nhp_id: Optional[Any] = None
    LINK: Optional[Any] = None
    START_DATE: Optional[Any] = None
    STOP_DATE: Optional[Any] = None
    TYPE: Optional[Any] = None
    PATIENT_ID: Optional[Any] = None
    EVENT_TYPE: Optional[Any] = None
    UID: Optional[Any] = None
    STUDY_DESIGN_NOTES: Optional[Any] = None
    DOSE: Optional[Any] = None
    TREATMENT_PARENT: Optional[Any] = None
    ORGAN_DETAIL: Optional[Any] = None
    ORGAN: Optional[Any] = None
    TREATMENT: Optional[Any] = None
    CFU: Optional[Any] = None
    NAME: Optional[Any] = None
    DOSE_UNITS: Optional[Any] = None
    PROTOCOL: Optional[Any] = None
    SAMPLE_ID: Optional[Any] = None
    ROUTE: Optional[Any] = None
    PARENT: Optional[Any] = None
    Treatment1: Optional[Any] = None
    Treatment1Type: Optional[Any] = None
    Treatment1Route: Optional[Any] = None
    Treatment1Date: Optional[Any] = None
    Treatment1Dose: Optional[Any] = None
    Treatment1DoseUnits: Optional[Any] = None
    Treatment2: Optional[Any] = None
    Treatment2Type: Optional[Any] = None
    Treatment2Route: Optional[Any] = None
    Treatment2Date: Optional[Any] = None
    Treatment2Dose: Optional[Any] = None
    Treatment2DoseUnits: Optional[Any] = None
    NecropsyDate: Optional[Any] = None
    AlternativeID: Optional[Any] = None
    Treatment3: Optional[Any] = None
    Treatment3Type: Optional[Any] = None
    Treatment3Route: Optional[Any] = None
    Treatment3Date: Optional[Any] = None
    Treatment3Dose: Optional[Any] = None
    Treatment3DoseUnits: Optional[Any] = None

class PAVInfo(BaseModel):
    pass