from __future__ import annotations

from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from scholarroute.infrastructure.db.models import (
    Category,
    Course,
    Degree,
    Exam,
    ExamType,
    GenderPool,
    InstitutionType,
    QuotaType,
    SeatType,
    State,
    Subject,
)

Reference = TypeVar(
    "Reference",
    Category,
    Course,
    Degree,
    Exam,
    ExamType,
    GenderPool,
    InstitutionType,
    QuotaType,
    SeatType,
    State,
    Subject,
)


def _ensure(  # noqa: UP047
    session: Session, model: type[Reference], code: str, name: str, **values: object
) -> Reference:
    existing = session.scalar(select(model).where(model.code == code))
    if existing is not None:
        return existing
    item = model(code=code, name=name, **values)
    session.add(item)
    session.flush()
    return item


def load_reference_data(session: Session) -> None:
    engineering = _ensure(session, ExamType, "ENGINEERING", "Engineering entrance")
    medical = _ensure(session, ExamType, "MEDICAL", "Medical entrance")
    _ensure(session, Exam, "JEE_MAIN", "JEE Main", exam_type_id=engineering.id)
    _ensure(session, Exam, "JEE_ADVANCED", "JEE Advanced", exam_type_id=engineering.id)
    _ensure(session, Exam, "NEET_UG", "NEET UG", exam_type_id=medical.id)
    _ensure(session, Course, "BTECH", "Bachelor of Technology")
    _ensure(session, Course, "MBBS", "Bachelor of Medicine and Bachelor of Surgery")
    _ensure(session, Degree, "BTECH", "B.Tech")
    _ensure(session, Degree, "MBBS", "MBBS")
    for code, name in (
        ("OPEN", "Open"),
        ("OBC_NCL", "Other Backward Classes - Non Creamy Layer"),
        ("SC", "Scheduled Caste"),
        ("ST", "Scheduled Tribe"),
        ("EWS", "Economically Weaker Section"),
        ("OPEN_PWD", "Open - Persons with Disabilities"),
        ("OBC_NCL_PWD", "OBC-NCL - Persons with Disabilities"),
        ("SC_PWD", "Scheduled Caste - Persons with Disabilities"),
        ("ST_PWD", "Scheduled Tribe - Persons with Disabilities"),
        ("EWS_PWD", "EWS - Persons with Disabilities"),
    ):
        _ensure(session, Category, code, name)
    for code, name in (
        ("ALL_INDIA", "All India"),
        ("HOME_STATE", "Home State"),
        ("OTHER_STATE", "Other State"),
    ):
        _ensure(session, QuotaType, code, name)
    _ensure(session, GenderPool, "GENDER_NEUTRAL", "Gender Neutral")
    _ensure(session, GenderPool, "FEMALE_ONLY", "Female Only")
    _ensure(session, SeatType, "REGULAR", "Regular")
    for code, name in (
        ("IIT", "Indian Institute of Technology"),
        ("NIT", "National Institute of Technology"),
        ("IIIT", "Indian Institute of Information Technology"),
        ("GFTI", "Government Funded Technical Institution"),
        ("MEDICAL_GOVERNMENT", "Government Medical College"),
        ("MEDICAL_PRIVATE", "Private Medical College"),
        ("DEEMED_UNIVERSITY", "Deemed University"),
    ):
        _ensure(session, InstitutionType, code, name)
    for code, name in (
        ("AN", "Andaman and Nicobar Islands"),
        ("AP", "Andhra Pradesh"),
        ("AR", "Arunachal Pradesh"),
        ("AS", "Assam"),
        ("BR", "Bihar"),
        ("CH", "Chandigarh"),
        ("CG", "Chhattisgarh"),
        ("DN", "Dadra and Nagar Haveli and Daman and Diu"),
        ("DL", "Delhi"),
        ("GA", "Goa"),
        ("GJ", "Gujarat"),
        ("HR", "Haryana"),
        ("HP", "Himachal Pradesh"),
        ("JK", "Jammu and Kashmir"),
        ("JH", "Jharkhand"),
        ("KA", "Karnataka"),
        ("KL", "Kerala"),
        ("LA", "Ladakh"),
        ("LD", "Lakshadweep"),
        ("MP", "Madhya Pradesh"),
        ("MH", "Maharashtra"),
        ("MN", "Manipur"),
        ("ML", "Meghalaya"),
        ("MZ", "Mizoram"),
        ("NL", "Nagaland"),
        ("OD", "Odisha"),
        ("PY", "Puducherry"),
        ("PB", "Punjab"),
        ("RJ", "Rajasthan"),
        ("SK", "Sikkim"),
        ("TN", "Tamil Nadu"),
        ("TS", "Telangana"),
        ("TR", "Tripura"),
        ("UP", "Uttar Pradesh"),
        ("UK", "Uttarakhand"),
        ("WB", "West Bengal"),
    ):
        _ensure(session, State, code, name)
    for code, name in (
        ("PHYSICS", "Physics"),
        ("CHEMISTRY", "Chemistry"),
        ("MATHEMATICS", "Mathematics"),
        ("BIOLOGY", "Biology"),
    ):
        _ensure(session, Subject, code, name)
