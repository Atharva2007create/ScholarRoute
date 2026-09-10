from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from scholarroute.entrypoints.api.dependencies import SessionDependency
from scholarroute.entrypoints.api.v1.schemas import PageMeta, ReferenceItem, ReferencePage
from scholarroute.errors import ApplicationError
from scholarroute.infrastructure.db.models import (
    AcademicYear,
    Board,
    Branch,
    Category,
    CounsellingAuthority,
    Course,
    Exam,
    GenderPool,
    InstitutionType,
    Program,
    QuotaType,
    State,
)
from scholarroute.infrastructure.db.models.enums import RecordStatus

router = APIRouter(prefix="/api/v1/reference", tags=["Reference Data"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]

MODELS: dict[str, Any] = {
    "exams": Exam,
    "boards": Board,
    "states": State,
    "categories": Category,
    "quotas": QuotaType,
    "gender-pools": GenderPool,
    "institution-types": InstitutionType,
    "counselling-authorities": CounsellingAuthority,
    "courses": Course,
}


@router.get("/{resource}", response_model=ReferencePage, summary="List reference values")
def list_reference(
    resource: str,
    session: SessionDependency,
    limit: Limit = 20,
    offset: Offset = 0,
) -> ReferencePage:
    if resource == "admission-years":
        year_rows = list(
            session.scalars(
                select(AcademicYear).order_by(AcademicYear.year.desc()).offset(offset).limit(limit)
            )
        )
        total = session.scalar(select(func.count()).select_from(AcademicYear)) or 0
        return ReferencePage(
            results=[
                ReferenceItem(id=row.id, code=str(row.year), name=row.label) for row in year_rows
            ],
            meta=PageMeta(total=total, limit=limit, offset=offset),
        )
    model = MODELS.get(resource)
    if model is None:
        raise ApplicationError("RESOURCE_NOT_FOUND", "Unknown reference resource", 404)
    statement = select(model).where(model.status == RecordStatus.ACTIVE).order_by(model.code)
    count = select(func.count()).select_from(model).where(model.status == RecordStatus.ACTIVE)
    rows = list(session.scalars(statement.offset(offset).limit(limit)))
    return ReferencePage(
        results=[
            ReferenceItem(id=row.id, code=row.code, name=getattr(row, "name", row.code))
            for row in rows
        ],
        meta=PageMeta(total=session.scalar(count) or 0, limit=limit, offset=offset),
    )


@router.get(
    "/branches/by-course/{course_id}",
    response_model=ReferencePage,
    summary="List branches for a course",
)
def branches_by_course(
    course_id: UUID,
    session: SessionDependency,
    limit: Limit = 20,
    offset: Offset = 0,
) -> ReferencePage:
    base = Branch.course_id == course_id
    rows = list(
        session.scalars(
            select(Branch)
            .where(base, Branch.status == RecordStatus.ACTIVE)
            .order_by(Branch.code)
            .offset(offset)
            .limit(limit)
        )
    )
    total = (
        session.scalar(
            select(func.count())
            .select_from(Branch)
            .where(base, Branch.status == RecordStatus.ACTIVE)
        )
        or 0
    )
    return ReferencePage(
        results=[ReferenceItem(id=row.id, code=row.code, name=row.name) for row in rows],
        meta=PageMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/programs/by-institution/{institution_id}",
    response_model=ReferencePage,
    summary="List programs for an institution",
)
def programs_by_institution(
    institution_id: UUID, session: SessionDependency, limit: Limit = 20, offset: Offset = 0
) -> ReferencePage:
    base = Program.institution_id == institution_id
    rows = list(
        session.scalars(
            select(Program)
            .where(base, Program.status == RecordStatus.ACTIVE)
            .order_by(Program.code)
            .offset(offset)
            .limit(limit)
        )
    )
    total = (
        session.scalar(
            select(func.count())
            .select_from(Program)
            .where(base, Program.status == RecordStatus.ACTIVE)
        )
        or 0
    )
    return ReferencePage(
        results=[ReferenceItem(id=row.id, code=row.code, name=row.name) for row in rows],
        meta=PageMeta(total=total, limit=limit, offset=offset),
    )
