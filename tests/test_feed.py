"""The plugin's own conversion of the Bank of Japan's recorded answers, every
value in them synthetic."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder

from bank_of_japan.answers import NotRead, Refused, parse
from bank_of_japan.feed import month_before
from bank_of_japan.portal import Fetched, SyntheticPortal, asked, path_for

from conftest import (
    AT,
    EUR,
    FX,
    HELD,
    INSTANCE,
    RATES,
    TERM,
    TONA,
    USD,
    feed,
    fx_want,
    resolving,
    want,
)


def rates_of(plugin: Recorder, subject: str, want_id: str | None = None) -> list[ops.Rate]:
    return [
        r
        for b in plugin.on("RecordRates")
        if want_id is None or b.want_id == want_id
        for r in b.rates
        if r.meta.subjects[0].entity_id == subject
    ]


def prices_of(plugin: Recorder, want_id: str) -> list[ops.Price]:
    return [p for b in plugin.on("RecordPrices") if b.want_id == want_id for p in b.prices]


def heard(*asked: object, plugin: Recorder | None = None, portal: object = None) -> Recorder:
    """The Bank checked, then each want heard."""
    held = plugin or resolving(Recorder(INSTANCE))
    work = feed(held, portal=portal)
    asyncio.run(work.check())
    for one in asked:
        held.answer("ObservationsWanted", lambda _, w=one: w.message)  # type: ignore[misc]
        asyncio.run(held.hear(work))
    return held


def on(rates: list[ops.Rate], day: str, tenor: tuple[int, int] | None = None) -> ops.Rate:
    return next(
        r
        for r in rates
        if r.meta.business_date == day and (tenor is None or (r.tenor.count, r.tenor.unit) == tenor)
    )


def test_the_check_records_nothing_and_resolves_every_subject() -> None:
    plugin = resolving(Recorder(INSTANCE), "Call Rate, Collateralized Overnight")
    portal = SyntheticPortal(lambda: AT)
    work = feed(plugin, portal=portal)
    done = asyncio.run(work.check())
    assert done == {d: date(2026, 11, 17) for d in ("FM01", "FM02", "FM08", "IR01")}
    assert not plugin.on("RecordRates") and not plugin.on("RecordPrices")
    missed = {i.value for p in plugin.on("ReportMissingInstrument") for i in p.identifiers}
    assert missed == {"Call Rate, Collateralized Overnight"}
    assert work.status.records["Call Rate, Uncollateralized"].instrument_id == TERM
    assert {c: h.instrument_id for c, h in work.status.currencies.items()} == {
        "USD": USD,
        "EUR": EUR,
    }
    # The month before and this one, Tokyo's: November 20th there.
    assert all("startDate=202610&endDate=202611" in p for p in portal.asked)
    assert asked(portal.asked[0]) == ("FM01", ["STRDCLUCON", "STRDCLUCV"])
    asyncio.run(work.check())
    assert len(plugin.on("ReportMissingInstrument")) == 1


def test_tona_with_its_volume_and_the_call_rates() -> None:
    plugin = heard(
        want("w-t", [TONA], day="2026-11-17"),
        want("w-c", [TERM], day="2026-11-17"),
    )
    tona = on(rates_of(plugin, TONA, "w-t"), "2026-11-17")
    assert tona.kind == ops.RATE_KIND_FIXING and str(as_decimal(tona.value.value)) == "0.479"
    assert tona.convention.day_count == ops.DAY_COUNT_ACT_365_FIXED
    assert tona.convention.compounding == ops.COMPOUNDING_SIMPLE
    assert str(as_decimal(tona.volume.amount)) == "2086300000000"
    assert tona.volume.currency_code == "JPY"
    assert not tona.meta.HasField("raw") and not tona.meta.source_times
    assert tona.meta.source.dataset == RATES
    term = rates_of(plugin, TERM, "w-c")
    week = on(term, "2026-11-17", (1, ops.TENOR_UNIT_WEEK))
    assert str(as_decimal(week.value.value)) == "0.493"
    # The 1-month and 3-month rates the Bank states nothing for that day.
    assert {(r.tenor.count, r.tenor.unit) for r in term} == {
        (1, ops.TENOR_UNIT_WEEK),
        (2, ops.TENOR_UNIT_MONTH),
    }


def test_the_basic_loan_rate_every_calendar_day() -> None:
    basic = HELD["The Basic Discount Rate and Basic Loan Rate"]
    plugin = heard(want("w-b", [basic], day="2026-10-04"))
    sunday = on(rates_of(plugin, basic, "w-b"), "2026-10-04")
    assert sunday.kind == ops.RATE_KIND_FIXING and str(as_decimal(sunday.value.value)) == "0.75"


def test_the_exchange_rates_never_inverted() -> None:
    plugin = heard(fx_want("w-usd", "2026-11-17"), fx_want("w-eur", "2026-11-17", EUR))
    usd = prices_of(plugin, "w-usd")
    assert [(p.meta.row_key, str(as_decimal(p.price.amount))) for p in usd] == [
        ("USDJPY:2026-11-17", "149.83")
    ]
    assert usd[0].price.currency_code == "JPY" and usd[0].kind == ops.PRICE_KIND_CLOSE
    assert usd[0].meta.subjects[0].entity_id == USD and usd[0].meta.source.dataset == FX
    assert not usd[0].meta.HasField("raw")
    eur = prices_of(plugin, "w-eur")
    assert [(p.price.currency_code, str(as_decimal(p.price.amount))) for p in eur] == [
        ("USD", "1.1487")
    ]
    assert eur[0].meta.subjects[0].entity_id == EUR


def test_a_range_ends_on_its_last_day() -> None:
    tokyo = ZoneInfo("Asia/Tokyo")
    asked_for = want("w-r", [TONA])
    asked_for.message.valid_from_ns = int(datetime(2026, 11, 12, tzinfo=tokyo).timestamp()) * 10**9
    # The last nanosecond of the 16th, Tokyo's: never rounded into the 17th.
    until = datetime(2026, 11, 17, tzinfo=tokyo).astimezone(UTC)
    asked_for.message.valid_until_ns = int(until.timestamp()) * 10**9
    plugin = heard(asked_for)
    days = [r.meta.business_date for r in rates_of(plugin, TONA, "w-r")]
    assert days == ["2026-11-12", "2026-11-13", "2026-11-16"]


def test_wants_declined() -> None:
    plugin = heard(
        want("w-1", [TONA], day="2026-10-01"),
        want("w-2", ["INS-ELSE"], day="2026-10-01"),
        want("w-3", [TONA], day="2026-10-04"),
        want("w-4", [TONA], day="2026-11-25"),
        fx_want("w-5", "2026-11-15"),
        want("w-6", [USD], day="2026-11-17"),
        want("w-7", [USD], day="2026-11-17", dataset=FX, data_type="meridian.v1.Rate"),
    )
    against = rates_of(plugin, TONA, "w-1")
    assert [r.meta.business_date for r in against] == ["2026-10-01"]
    reasons = [(d.want_id, ops.UnansweredReason.Name(d.reason)) for d in plugin.on("DeclineWant")]
    assert reasons == [
        ("w-2", "UNANSWERED_REASON_NOT_COVERED"),
        ("w-3", "UNANSWERED_REASON_SOURCE_SILENT"),
        ("w-4", "UNANSWERED_REASON_SOURCE_SILENT"),
        ("w-5", "UNANSWERED_REASON_SOURCE_SILENT"),
        ("w-6", "UNANSWERED_REASON_NOT_COVERED"),
        ("w-7", "UNANSWERED_REASON_NOT_COVERED"),
    ]


def test_the_latest_wanted() -> None:
    plugin = heard(want("w-l", [TONA]), want("w-c", [TERM]))
    assert [r.meta.business_date for r in rates_of(plugin, TONA, "w-l")] == ["2026-11-17"]
    assert {r.meta.business_date for r in rates_of(plugin, TERM, "w-c")} == {"2026-11-17"}


def test_a_revised_value_is_the_same_rows_next_version() -> None:
    class Revised(SyntheticPortal):
        reads = 0

        async def get(self, path: str) -> Fetched:
            got = await super().get(path)
            if "db=FM01" not in path:
                return got
            Revised.reads += 1
            if Revised.reads < 3:
                return got
            body = got.text.replace(",20261117,0.479", ",20261117,0.481")
            return Fetched(path, 200, body.encode(), got.fetched_at, got.date)

    plugin = heard(
        want("w-a", [TONA], day="2026-11-17"),
        want("w-b", [TONA], day="2026-11-17"),
        portal=Revised(lambda: AT),
    )
    first, second = rates_of(plugin, TONA, "w-a")[0], rates_of(plugin, TONA, "w-b")[0]
    assert first.meta.row_key == second.meta.row_key
    assert str(as_decimal(second.value.value)) == "0.481"


def test_the_bank_not_answering_is_said() -> None:
    class Down(SyntheticPortal):
        async def get(self, path: str) -> Fetched:
            return Fetched(path, 503, b"Service Unavailable", AT)

    plugin = resolving(Recorder(INSTANCE))
    work = feed(plugin, portal=Down(lambda: AT))
    assert asyncio.run(work.check()) == {}
    assert "answered 503" in work.status.sources["FM01"].error
    assert work.status.sources["FM01"].read_at is None


def test_a_further_page_is_read_on() -> None:
    class Paged(SyntheticPortal):
        async def get(self, path: str) -> Fetched:
            got = await super().get(path)
            if "db=FM08" not in path:
                return got
            lines = got.text.splitlines()
            head = [line for line in lines if not line.startswith("FXERD")]
            usd = [line for line in lines if line.startswith("FXERD04")]
            eur = [line for line in lines if line.startswith("FXERD34")]
            if "startPosition=2" in path:
                return Fetched(path, 200, "\n".join([*head, *eur]).encode(), AT)
            head = [("NEXTPOSITION,2" if h == "NEXTPOSITION," else h) for h in head]
            return Fetched(path, 200, "\n".join([*head, *usd]).encode(), AT)

    portal = Paged(lambda: AT)
    plugin = heard(fx_want("w-eur", "2026-11-17", EUR), portal=portal)
    assert [str(as_decimal(p.price.amount)) for p in prices_of(plugin, "w-eur")] == ["1.1487"]
    assert any("startPosition=2" in p for p in portal.asked)


def test_the_answers_read_as_written() -> None:
    recording = SyntheticPortal(lambda: AT).recordings["FM02"]
    read = parse("\n".join([*recording.head, *recording.lines]), "FM02")
    assert read.units["STRDCLUC1W"] == "percent per annum" and not read.unread
    assert read.days[0] == date(2026, 10, 1) and read.days[-1] == date(2026, 11, 17)
    assert read.names["STRDCLCOON"] == "Call Rate, Collateralized Overnight/Daily"
    with pytest.raises(NotRead):
        parse("Not found", "FM02")
    with pytest.raises(NotRead):
        parse("\n".join(recording.head), "FM08")
    with pytest.raises(Refused) as refused:
        parse('{"STATUS":400,"MESSAGEID":"M181013E","MESSAGE":"Nonexistent series code"}', "FM02")
    assert refused.value.message_id == "M181013E"


def test_the_request_names_months() -> None:
    path = path_for("FM01", ["STRDCLUCON", "STRDCLUCV"], date(2025, 12, 3), date(2026, 1, 9))
    assert path == (
        "/api/v1/getDataCode?format=csv&lang=en&db=FM01&code=STRDCLUCON,STRDCLUCV"
        "&startDate=202512&endDate=202601"
    )
    assert month_before(date(2026, 1, 20)) == date(2025, 12, 1)
    assert "code=MADR1Z@D" in path_for("IR01", ["MADR1Z@D"], date(2026, 1, 1), date(2026, 1, 1))
