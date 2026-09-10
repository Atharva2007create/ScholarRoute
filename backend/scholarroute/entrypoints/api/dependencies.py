from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from scholarroute.infrastructure.db.session import get_session


def transactional_session() -> Generator[Session, None, None]:
    for session in get_session():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


SessionDependency = Annotated[Session, Depends(transactional_session)]
