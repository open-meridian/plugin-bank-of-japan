"""The Bank of Japan's TONA, money-market rates and exchange rates as an Open
Meridian data plugin (the product owner, items 128, 132, 140 and 175,
2026-11-19: Tier 1, served, not kept).

It runs its data role class, `Lake` (feed.py's `Feed`, with its lifecycle
here), with `meridian.run` on the sidecar it is launched beside, declaring
its catalogue and its one setting (declaration.py). It asks the Bank's API at
start and every hour whether it answers, recording nothing, and reads any
day when the lake wants it (feed.py). It keeps nothing the Bank answered.
It reads which of its datasets a deployment admin has licensed, on start and
every minute. It holds nothing else: a restart asks the Bank again, and the
lake answers what it recorded before unchanged.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

import meridian

from .declaration import DECLARATION, PORT
from .feed import Feed
from .page import figures, hold, pages
from .portal import portal
from .settings import Config, config_from

log = logging.getLogger("bank_of_japan")

#: How often the Bank is checked, in seconds: hourly.
CHECK_SECONDS = 3600
#: How often the datasets' licences are read again.
LICENCES_SECONDS = 60


class Lake(Feed):
    """The data role's class with its lifecycle (open-meridian 0.35, rulings
    1004, 1005, 1009 to 1023): `meridian.run` delivers each settings to
    `on_settings` -- the first before anything is heard -- and starts `run`,
    again after a backoff should it fail."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = Config()
        self.wake = asyncio.Event()

    async def on_settings(self, delivered: Any) -> None:
        """Apply each delivery of the settings: sample data on or off."""
        self.config = config_from(delivered.values)
        self.use(portal(self.config.sample_data))
        self.wake.set()

    async def run(self) -> None:
        """The Bank checked, the licences read."""
        await asyncio.gather(self._check(), self._licences())

    async def _check(self) -> None:
        """Check the Bank at once, then hourly, or at once when the settings
        change."""
        while True:
            self.wake.clear()
            try:
                await self.check()
            except meridian.MeridianError as failed:
                # The sidecar refused something a check needed; say so and
                # keep the schedule rather than spin.
                for held in self.status.sources.values():
                    held.error = f"the deployment refused a request: {failed}"
                log.warning("this check stopped: %s", failed)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.wake.wait(), timeout=CHECK_SECONDS)

    async def _licences(self) -> None:
        """Its own declared datasets' licences (contract v20, W10.9), read on
        start and every minute, for the Datasets page."""
        while True:
            try:
                await self.wants.read_licences()
            except meridian.MeridianError as failed:
                log.warning("the datasets' licences were not read this time: %s", failed)
            await asyncio.sleep(LICENCES_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    lake = Lake(portal(False))
    hold(lake)
    # The version's whole declaration (declaration.py): its settings, its
    # pages with the levels each serves and their tools, and its
    # documentation. A version registers exactly what it was uploaded with
    # (contract v25).
    meridian.run(
        declaration=DECLARATION,
        roles=[lake],
        pages=pages,
        port=PORT,
        on_settings=lake.on_settings,
        figures=lambda: figures(lake.status, lake),
    )


if __name__ == "__main__":
    main()
