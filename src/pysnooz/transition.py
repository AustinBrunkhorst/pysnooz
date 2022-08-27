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

        await self._update_task

    async def _async_run(
        self,
        start_value: float,
        end_value: float,
        duration: timedelta,
        async_on_update: Callable[[float], Awaitable[None]],
        async_on_complete: Callable[[], Awaitable[None]],
    ) -> None:
        self.start_time = datetime.now()
        self.end_time = self.start_time + duration

        self.last_update = self.start_time

        while not self._cancelled and (current_time := datetime.now()) <= self.end_time:
            progress = (current_time - self.start_time) / duration
            value = start_value + (end_value - start_value) * progress
            _LOGGER.debug(f"{progress * 100:.2f}%: {value:.2f}")
            await async_on_update(value)
            elapsed = current_time - self.last_update
            self.last_update = current_time
            await asyncio.sleep(max(0, (1 / UPDATES_PER_SECOND) - elapsed.seconds))

        if not self._cancelled:
            await async_on_update(end_value)
            await async_on_complete()

    def cancel(self) -> None:
        if self._update_task is None:
            return

        self._cancelled = True
        self._update_task.cancel()
        self._update_task = None
