from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from roadeye.config import settings
from roadeye.contracts import Clock

engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class UTCClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


clock: Clock = UTCClock()


def now() -> datetime:
    return clock.now()


def session() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
