import sys
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.db import make_engine, init_db  # noqa: E402
from ase.seed import seed_uses  # noqa: E402


@pytest.fixture
def db():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed_uses(session)
    yield session
    session.close()
