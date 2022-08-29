from __future__ import annotations

import asyncio
import logging
from asyncio import AbstractEventLoop, Task
from datetime import datetime, timedelta
from typing import Awaitable, Callable

UPDATES_PER_SECOND = 6

_LOGGER = logging.getLogger(__name__)


class Transition:
    start_time: datetime | None = None
    end_time: datetime | None = None
    last_update: datetime | None = None

    _run_id: int = 0
    _cancelled: bool = False
    _update_task: Task[None] | None = None

    async def async_run(
        self,
        loop: AbstractEventLoop,
        start_value: float,
        end_value: float,
        duration: timedelta,
        async_on_update: Callable[[float], Awaitable[None]],
        async_on_complete: Callable[[], Awaitable[None]],
    ) -> None:
        self._cancelled = False
        self._update_task = loop.create_task(
            self._async_run(
                start_value,
                end_value,
                duration,
                async_on_update,
                async_on_complete,
            ),
            name=f"Transition from {start_value} to {end_value} over {duration}",
        )

        try:
            await self._update_task
        finally:
            self._run_id += 1

    async def _async_run(
        self,
        start_value: float,
        end_value: float,
        duration: timedelta,
        async_on_update: Callable[[float], Awaitable[None]],
        async_on_complete: Callable[[], Awaitable[None]],
    ) -> None:
        start_time = datetime.now()
        self.start_time = start_time
        end_time = start_time + duration
        self.end_time = end_time

        self.last_update = start_time

        async def dispatch_update(value: float) -> None:
            _LOGGER.debug(f"[{self._run_id}] {progress * 100:.1f}%: {value:.2f}")
            await async_on_update(value)

        async def dispatch_complete() -> None:
            _LOGGER.debug(f"[{self._run_id}] complete in {datetime.now() - start_time}")
            await async_on_complete()

        _LOGGER.debug(
            f"[{self._run_id}] starting {start_value} -> {end_value} over {duration}"
        )

        while not self._cancelled and (current_time := datetime.now()) <= end_time:
            progress = (current_time - start_time) / duration
            value = start_value + (end_value - start_value) * progress
            await dispatch_update(value)
            elapsed = current_time - self.last_update
            self.last_update = current_time
            await asyncio.sleep(max(0, (1 / UPDATES_PER_SECOND) - elapsed.seconds))

        if not self._cancelled:
            await dispatch_update(end_value)
            await dispatch_complete()

    def cancel(self) -> None:
        if self._update_task is None or self._update_task.done():
            return

        self._cancelled = True
        self._update_task.cancel()
        self._update_task = None

        duration = (
            "" if not self.start_time else f" after {datetime.now() - self.start_time}"
        )
        _LOGGER.debug(f"[{self._run_id}] cancelled{duration}")
