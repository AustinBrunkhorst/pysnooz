import asyncio
from datetime import timedelta
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from pysnooz.transition import Transition


@pytest.mark.asyncio
async def test_increasing_value(
    mocker: MockerFixture, event_loop: asyncio.AbstractEventLoop, mock_sleep: None
) -> None:
    await _standard_transition_test(0, 31, timedelta(seconds=30), mocker, event_loop)


@pytest.mark.asyncio
async def test_decreasing_value(
    mocker: MockerFixture, event_loop: asyncio.AbstractEventLoop, mock_sleep: None
) -> None:
    await _standard_transition_test(94, 15, timedelta(seconds=30), mocker, event_loop)


@pytest.mark.asyncio
async def test_short_duration(
    mocker: MockerFixture, event_loop: asyncio.AbstractEventLoop, mock_sleep: None
) -> None:
    await _standard_transition_test(100, 250, timedelta(seconds=1), mocker, event_loop)


@pytest.mark.asyncio
async def test_cancel(
    mocker: MockerFixture, event_loop: asyncio.AbstractEventLoop, mock_sleep: None
) -> None:
    transition = Transition()

    start_value = 0
    end_value = 100
    cancel_after_value = 65

    def update_side_effect(value: float) -> None:
        if value >= cancel_after_value:
            transition.cancel()

    on_update = mocker.async_stub(name="on_update")
    on_update.side_effect = update_side_effect

    on_complete = mocker.async_stub(name="on_complete")

    with pytest.raises(asyncio.CancelledError):
        await transition.async_run(
            event_loop,
            start_value,
            end_value,
            timedelta(seconds=10),
            on_update,
            on_complete,
        )

    # ensure no additional calls made after cancelled
    assert not [
        c for c in on_update.mock_calls if round(c.args[0]) > cancel_after_value
    ]
    on_complete.assert_not_called()


async def _standard_transition_test(
    start_value: float,
    end_value: float,
    duration: timedelta,
    mocker: MockerFixture,
    event_loop: asyncio.AbstractEventLoop,
) -> None:
    transition = Transition()

    on_update = mocker.async_stub(name="on_update")
    on_complete = mocker.async_stub(name="on_complete")

    start_value = 94
    end_value = 15
    await transition.async_run(
        event_loop,
        start_value,
        end_value,
        duration,
        on_update,
        on_complete,
    )

    assert on_update.mock_calls[0] == call(start_value)
    assert on_update.mock_calls[-1] == call(end_value)
    on_complete.assert_called_once()
