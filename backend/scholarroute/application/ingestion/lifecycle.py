from __future__ import annotations

from scholarroute.infrastructure.db.models.enums import StagedRecordStatus

ALLOWED_TRANSITIONS: dict[StagedRecordStatus, set[StagedRecordStatus]] = {
    StagedRecordStatus.RAW: {StagedRecordStatus.PARSED, StagedRecordStatus.REJECTED},
    StagedRecordStatus.PARSED: {StagedRecordStatus.NORMALIZED, StagedRecordStatus.REJECTED},
    StagedRecordStatus.NORMALIZED: {StagedRecordStatus.VALIDATED, StagedRecordStatus.REJECTED},
    StagedRecordStatus.VALIDATED: {StagedRecordStatus.PUBLISHED, StagedRecordStatus.REJECTED},
    StagedRecordStatus.PUBLISHED: set(),
    StagedRecordStatus.REJECTED: set(),
}


def transition(current: StagedRecordStatus, target: StagedRecordStatus) -> StagedRecordStatus:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid staged-record transition: {current} -> {target}")
    return target
