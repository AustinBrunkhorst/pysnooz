import asyncio
from typing import Any, Iterator

import pytest
from freezegun import freeze_time


@pytest.fixture(scope="function")
def mock_sleep(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    with freeze_time() as freeze:

        async def sleep(seconds, loop=None):
            freeze.tick(seconds)

        monkeypatch.setattr(asyncio, "sleep", sleep)

        yield freeze
