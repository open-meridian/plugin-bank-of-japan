"""The data suite (meridian.suites), each case the Bank of Japan's series
present mapped to the plugin's own conversion of the Bank's recorded answers,
the whole suite passing.

Both datasets are pulled only (ruling 132), so every case recording a value
does it through a want.

Presented: the exchange rates' price cases (each a close of one currency's
cash instrument in another, exact, a correction the same row's next version,
the US dollar resolving to two records, a want recorded against and a
subject declined); `a-same-day-revision` (TONA revised) and
`a-tenor-not-published` (the uncollateralized call rates of 17 November
2026: the 1-week and 2-month rates alone); the wants and licences cases.

Not presented, each with why: every case about a kind of data the Bank
never publishes here (bars, trades, quotes, venues, crypto, outcomes,
chains, filings, holdings, dividends, ratings, pools, derived series); the
calendar cases (no calendar declared); `a-rate-fixing` (it asks for
percentiles, which the Bank does not state), `an-index-level` (no index
level here), `a-curve-for-a-date` (no par yield here),
`two-conventions-one-tenor`, `a-curve-point-from-another-source`;
`a-daily-close` and `reports-its-feed-delay` (the Bank states no published
time); `records-a-datasets-liveness`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import ANSWERED_BY_SDK, Recorder, run, suite

from bank_of_japan.feed import Feed
from bank_of_japan.portal import Fetched, SyntheticPortal

from conftest import AT, FX, INSTANCE, RATES, TERM, TONA, USD, feed, fx_want, resolving, want

NEVER = {
    "bars": "the Bank states one rate a day: no open, high, low or volume",
    "a crypto asset's price": "the Bank rates currencies: no token",
    "prices on a venue": "the Bank's rates are its own, no venue's",
    "a security's price": "the Bank rates currencies: no security another source named",
    "trades": "the Bank states one rate a day: no trades",
    "quotes": "the Bank states one rate a day: no quotes",
    "settlement dates": "records each value as published; never computes a settlement date",
    "outcomes": "the Bank publishes no event contract, so no outcome",
    "disputed outcomes": "the Bank publishes no event contract, so no outcome disputed",
    "streams": "it asks the Bank when wanted; it streams nothing",
    "option chains": "the Bank publishes no option chain",
    "filings": "the Bank publishes rates: no company's filings",
    "holdings": "the Bank publishes rates: no holdings report",
    "corporate actions": "the Bank publishes rates: no declared dividend",
    "ratings": "the Bank publishes rates: no rating",
    "derived series": "the Bank's values are recorded as published: no series derived from them",
    "factors": "the Bank publishes rates: no pool, so no pool's factor",
    "calendars": "its datasets declare no calendar: the platform holds none for the yen yet",
    "publication times": "the Bank states no published time for a value",
}
NOT_PRESENTED = {
    **{c.name: NEVER[c.about] for c in suite("data").cases if c.about in NEVER},
    "a-rate-fixing": "the Bank states no percentiles for TONA",
    "an-index-level": "the Bank publishes no index level here",
    "a-curve-for-a-date": "the Bank publishes call rates by term here: no par yield",
    "two-conventions-one-tenor": "the Bank publishes one convention a point here",
    "a-curve-point-from-another-source": "the Bank publishes no curve point another source does",
    "queries-the-lake-within-bounds": "it records no trades",
    "a-daily-close": "the Bank states no published time for a rate",
}


class Changed(SyntheticPortal):
    """The Bank, read twice a database: as recorded, then with TONA of
    17 November revised and the dollar's rate of 17 November corrected."""

    def __init__(self) -> None:
        super().__init__(lambda: AT)
        self.reads: dict[str, int] = {}

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        database = "FM01" if "db=FM01" in path else "FM08" if "db=FM08" in path else ""
        self.reads[database] = self.reads.get(database, 0) + 1
        if not database or self.reads[database] <= 2:
            return got
        old, new = (
            (",20261117,0.479", ",20261117,0.481")
            if database == "FM01"
            else (",20261117,149.83", ",20261117,149.91")
        )
        assert old in got.text
        body = got.text.replace(old, new).encode()
        return Fetched(path, 200, body, got.fetched_at, got.date)


async def _hear(recorder: Recorder, work: Feed, message: Any) -> None:
    recorder.answer("ObservationsWanted", lambda _: message)
    await recorder.hear(work)


def producers() -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    async def read(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(recorder)
        await work.check()
        await _hear(recorder, work, fx_want("w-fx", "2026-11-17").message)

    async def changed(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(recorder, portal=Changed())
        await work.check()
        await _hear(recorder, work, fx_want("w-a", "2026-11-17").message)
        await _hear(recorder, work, want("w-t", [TONA], day="2026-11-17").message)
        await _hear(recorder, work, fx_want("w-b", "2026-11-17").message)
        await _hear(recorder, work, want("w-u", [TONA], day="2026-11-17").message)

    async def two_records(recorder: Recorder) -> None:
        resolving(recorder, ambiguous="USD")
        await feed(recorder).check()

    async def gap(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(recorder)
        await work.check()
        await _hear(recorder, work, want("w-g", [TERM], day="2026-11-17").message)
        sent = [r for b in recorder.on("RecordRates") for r in b.rates]
        assert {(r.tenor.count, r.tenor.unit) for r in sent} == {
            (1, ops.TENOR_UNIT_WEEK),
            (2, ops.TENOR_UNIT_MONTH),
        }

    def wanted(message: Any) -> Callable[[Recorder], Awaitable[None]]:
        async def produce(recorder: Recorder) -> None:
            resolving(recorder)
            work = feed(recorder)
            await work.check()
            await _hear(recorder, work, message)

        return produce

    async def licences(recorder: Recorder) -> None:
        recorder.answer(
            "ListDatasets",
            lambda _: ops.ListDatasetsResult(licences=[ops.DatasetLicence(dataset=FX)]),
        )
        work = feed(recorder)
        await work.wants.read_licences()
        assert work.wants.licensed == {FX}

    async def withdrawn(recorder: Recorder) -> None:
        resolving(recorder)
        work = feed(recorder)
        recorder.answer(
            "WantWithdrawn", lambda _: ops.WantWithdrawnEvent(want_id="w-s", dataset=RATES)
        )
        await recorder.hear(work)

    return {
        "the-forming-day-restated": changed,
        "an-exact-price": read,
        "an-fx-rate": read,
        "an-asset-that-does-not-resolve": two_records,
        "a-want-recorded-against": wanted(fx_want("w-1", "2026-10-01").message),
        "a-subject-declined": wanted(fx_want("w-2", "2026-10-01", "LCL-CAD").message),
        "a-standing-want-withdrawn": withdrawn,
        "reads-its-datasets-licences": licences,
        "a-same-day-revision": changed,
        "a-tenor-not-published": gap,
    }


def test_the_data_suite_passes() -> None:
    report = run("data", producers(), not_presented=NOT_PRESENTED, instance_id=INSTANCE)
    assert report.passed, report.failures
    assert sorted(report.not_presented) == sorted(NOT_PRESENTED)
    assert len(report.passed_cases) == 10 + len(ANSWERED_BY_SDK)
    assert USD
