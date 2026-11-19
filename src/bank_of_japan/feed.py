"""The Bank of Japan's rates and exchange rates into the lake: every day of
either dataset recorded when the lake wants it (W10.4, W10.7), through the
SDK's rates helpers (`meridian.roles.data.rates`) and its `Wants`.

**Pull only** (ruling 132, declared.py). Nothing is pushed: a want is read
from the Bank's API when it is heard, and what the Bank answered is never
kept in the plugin's storage, so no row names a raw record.

**The check.** At start and every hour, each database is asked for its
series over the month before and this one, Tokyo's, and nothing of it is
recorded: the check says whether the Bank answers and the latest day it
states, for the Connection page, and resolves the subjects, so each the
deployment does not hold is reported missing and a want can name each one
it does.

**Rows** (series.py says each): TONA a `fixing` with its day's volume in
yen; the collateralized overnight call rate and the basic loan rate
`fixing`s; the uncollateralized call rates `fixing`s at their tenors on
their curve's record; each exchange rate a `close` `Price` of one
currency's cash instrument in the other. A value the Bank states nothing for
is no row, never a zero. Each is read from the Bank's text as a `Decimal`,
never a float. A value the Bank revises -- TONA's provisional figure made
final the next morning, a correction -- is the same row key's next version.

**Published time.** The API states no time on a value: no row states one,
rather than a wrong one.

**Subjects.** Each record by its code at `boj` (series.py), the US dollar
and the euro by their ISO 4217 codes, resolved once per process; one the
deployment does not hold is reported missing, and its values wait. The
plugin mints nothing.

**Wants.** A want of either dataset, for subjects the plugin records -- a
business date, a range of at most a year, or the latest -- is read from the
Bank and recorded against the want; a day the Bank states nothing for, or
one not come yet, is declined `source_silent`; any other subject, or another
kind of data, `not_covered`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import meridian
from meridian.operations import Money, ObservationMeta, Price, SubjectRef
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import data
from meridian.roles.data import rates

from .answers import NotRead, Table, parse
from .declared import DAY_TIME_ZONE, KEYS, PRICE, RATE
from .portal import Fetched, Portal, PortalUnreachable, path_for, utc_now
from .series import (
    CODES,
    CURRENCIES,
    DATABASES,
    DATABASES_OF,
    FM08,
    FX,
    FX_COLUMNS,
    JPY,
    RATE_COLUMNS,
    RECORDS,
    SOURCE,
    VOLUME,
    VOLUME_UNIT,
    Column,
    Record,
)

log = logging.getLogger("bank_of_japan")

TOKYO = ZoneInfo(DAY_TIME_ZONE)
#: The most days one want is answered for: a year.
MOST_DAYS = 366
#: The most pages one read follows: the API's limit is never near.
MOST_PAGES = 10


def _ns(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000) * 1000


def day_bounds(day: date) -> tuple[int, int]:
    start = datetime.combine(day, time(0, 0), TOKYO)
    return _ns(start), _ns(datetime.combine(day + timedelta(days=1), time(0, 0), TOKYO))


def month_before(day: date) -> date:
    """The first day of the month before `day`'s."""
    return (day.replace(day=1) - timedelta(days=1)).replace(day=1)


@dataclass(frozen=True)
class Outcome:
    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    unresolved: tuple[str, ...] = ()


@dataclass
class Held:
    """A record or a currency as the plugin last saw it: the deployment's
    instrument, or why there is none, and the latest day recorded."""

    code: str
    name: str = ""
    instrument_id: str = ""
    miss: str = ""
    latest_day: date | None = None


@dataclass
class SourceStatus:
    """What the plugin last did with one database, for its pages."""

    source: str
    checked_at: datetime | None = None
    read_at: datetime | None = None
    error: str = ""
    latest_day: date | None = None
    fetches: int = 0
    unread: dict[str, int] = field(default_factory=dict)


@dataclass
class Status:
    """What the plugin last did, for its pages; lost on a restart."""

    mode: str = "live"
    started_at: datetime | None = None
    sources: dict[str, SourceStatus] = field(
        default_factory=lambda: {d: SourceStatus(d) for d in DATABASES}
    )
    records: dict[str, Held] = field(default_factory=dict)
    currencies: dict[str, Held] = field(default_factory=dict)

    @property
    def checked_at(self) -> datetime | None:
        stamps = [s.checked_at for s in self.sources.values() if s.checked_at]
        return max(stamps) if stamps else None

    @property
    def error(self) -> str:
        return next((s.error for s in self.sources.values() if s.error), "")

    @property
    def fetches(self) -> int:
        return sum(s.fetches for s in self.sources.values())

    @property
    def read(self) -> bool:
        return any(s.read_at for s in self.sources.values())

    @property
    def misses(self) -> list[str]:
        return [h.code for h in [*self.records.values(), *self.currencies.values()] if h.miss]


class Feed(data.Role):
    """The plugin's data role class, its acts made on itself -- registered
    with `meridian.run`, or bound to the suite's recorder in its tests."""

    def __init__(self, portal: Portal, now: Callable[[], datetime] = utc_now) -> None:
        self.portal = portal
        self.now = now
        self.wants = data.Wants(self, KEYS, clock_ns=lambda: _ns(self.now()))
        self.rates = rates.Feed(
            self, SOURCE, wants=self.wants, day_zone=DAY_TIME_ZONE, clock_ns=lambda: _ns(self.now())
        )
        self.status = Status(mode=portal.mode, started_at=now())

    def today(self) -> date:
        return self.now().astimezone(TOKYO).date()

    def use(self, portal: Portal) -> None:
        """Read from `portal` from now on: sample data turned on or off."""
        if portal.mode != self.portal.mode:
            self.portal = portal
            self.status.mode = portal.mode

    # ── Reading ─────────────────────────────────────────────────────────

    async def read(self, database: str, start: date, end: date) -> Table:
        """`database`'s series from `start`'s month to `end`'s, every page of
        the answer read. PortalUnreachable or NotRead otherwise."""
        held = self.status.sources[database]
        held.checked_at = self.now()
        table: Table | None = None
        position = 0
        try:
            for _ in range(MOST_PAGES):
                fetched: Fetched = await self.portal.get(
                    path_for(database, CODES[database], start, end, position)
                )
                held.fetches += 1
                if fetched.status != 200 and not fetched.text.lstrip().startswith("{"):
                    raise PortalUnreachable(f"{fetched.url[:120]} answered {fetched.status}")
                page = parse(fetched.text, database)
                if table is None:
                    table = page
                else:
                    table.extend(page)
                position = page.next_position
                if not position:
                    break
        except (PortalUnreachable, NotRead) as failed:
            held.error = str(failed)
            raise
        assert table is not None
        held.error, held.read_at = "", self.now()
        if table.days:
            last = table.days[-1]
            held.latest_day = max(last, held.latest_day) if held.latest_day else last
        for line in table.unread:
            held.unread[line] = held.unread.get(line, 0) + 1
        return table

    # ── Resolving ───────────────────────────────────────────────────────

    async def record_of(self, record: Record) -> str:
        """A record's instrument, by its code at `boj`; empty, reported
        missing, where the deployment holds none."""
        held = self.status.records.setdefault(record.code, Held(record.code, record.description))
        if held.instrument_id:
            return held.instrument_id
        found = await self.rates.subject(
            record.identifier,
            description=record.description,
            instrument_type=record.instrument_type,
        )
        held.instrument_id, held.miss = found, "" if found else "not held: reported missing"
        return found

    async def currency(self, code: str) -> str:
        """A currency's cash instrument by ISO 4217, resolved now where not
        yet; empty, reported missing with why, where none resolves."""
        held = self.status.currencies.setdefault(code, Held(code, f"{code} cash"))
        if held.instrument_id:
            return held.instrument_id
        identifier = ops.Identifier(scheme="iso4217", value=code)
        found = await self.resolve_identifier(
            identifiers=[identifier],
            as_of_ns=_ns(self.now()),
            stated_asset_class="cash",
            stated_currency=code,
            stated_description=f"{code} cash",
        )
        if found.found and found.instrument_id:
            held.instrument_id, held.miss = found.instrument_id, ""
            return str(found.instrument_id)
        if held.miss:
            return ""
        reason = found.miss_reason or ops.MISS_REASON_NOT_FOUND
        held.miss = ops.MissReason.Name(reason).removeprefix("MISS_REASON_").lower()
        await self.report_missing_instrument(
            source=SOURCE,
            asset_class="cash",
            identifiers=[identifier],
            reason=reason,
            as_of_ns=_ns(self.now()),
            observed_at_ns=_ns(self.now()),
        )
        return ""

    async def resolve_pulled(self) -> None:
        """Every subject, resolved so a want can name it: the datasets are
        read only when wanted, so nothing else resolves them."""
        for record in RECORDS:
            await self.record_of(record)
        for code in CURRENCIES:
            await self.currency(code)

    # ── Recording ───────────────────────────────────────────────────────

    def _note(self, held: Held, day: date) -> None:
        if held.latest_day is None or day > held.latest_day:
            held.latest_day = day

    async def _rate_rows(
        self, read: Table, dataset: str, days: set[date] | None
    ) -> list[tuple[Any, Held]]:
        rows: list[tuple[Any, Held]] = []
        for seen in read.observations:
            column: Column | None = RATE_COLUMNS.get(seen.series)
            if column is None or column.database != read.name or dataset == FX:
                continue
            if days is not None and seen.day not in days:
                continue
            subject = await self.record_of(column.record)
            if not subject:
                continue
            extra: dict[str, Any] = {}
            stated = read.on(seen.day)
            if seen.series == "STRDCLUCON" and VOLUME in stated:
                extra["volume"] = Money(stated[VOLUME].value * VOLUME_UNIT, JPY)
            row = self.rates.rate(
                subject,
                dataset,
                column.kind,
                rates.percent(seen.text),
                business_date=seen.day,
                convention=column.convention,
                tenor=column.tenor or None,
                series=column.record.code,
                **extra,
            )
            rows.append((row, self.status.records[column.record.code]))
        return rows

    async def _prices(
        self, read: Table, dataset: str, days: set[date] | None
    ) -> list[tuple[Any, Held]]:
        prices: list[tuple[Any, Held]] = []
        if read.name != FM08 or dataset != FX:
            return prices
        source = self.wants.dataset(dataset)
        for seen in read.observations:
            if seen.series not in FX_COLUMNS or (days is not None and seen.day not in days):
                continue
            code, quoted = FX_COLUMNS[seen.series]
            subject = await self.currency(code)
            if not subject:
                continue
            start, end = day_bounds(seen.day)
            price = Price(
                meta=ObservationMeta(
                    row_key=f"{code}{quoted}:{seen.day.isoformat()}",
                    subjects=[SubjectRef(entity_id=subject)],
                    source=ops.Source(dataset=source),
                    valid_from_ns=start,
                    valid_until_ns=end,
                    business_date=seen.day.isoformat(),
                ),
                kind="close",
                price=Money(seen.value, quoted),
                basis="per_unit",
            )
            prices.append((price, self.status.currencies[code]))
        return prices

    async def record(
        self,
        read: Table,
        dataset: str,
        *,
        want_id: str = "",
        days: Iterable[date] | None = None,
        subjects: set[str] | None = None,
        latest: bool = False,
    ) -> tuple[Outcome, set[str]]:
        """Record `dataset`'s values in `read` -- on `days` and for
        `subjects` where given, each subject's latest day alone where
        `latest` -- against `want_id` where given. What the lake answered,
        and the subjects a row was sent for."""
        wanted = set(days) if days is not None else None
        rate_rows = await self._rate_rows(read, dataset, wanted)
        prices = await self._prices(read, dataset, wanted)
        if subjects is not None:
            rate_rows = [r for r in rate_rows if r[0].meta.subjects[0].entity_id in subjects]
            prices = [p for p in prices if p[0].meta.subjects[0].entity_id in subjects]
        if latest:
            rate_rows, prices = _latest(rate_rows), _latest(prices)
        for row, held in [*rate_rows, *prices]:
            self._note(held, date.fromisoformat(row.meta.business_date))
        counts = self.wants.sent_to(dataset)
        before = (counts.recorded, counts.restated, counts.unchanged)
        if rate_rows:
            await self.rates.record(dataset, [r for r, _ in rate_rows], want_id)
        if prices:
            await self.wants.record("prices", [p for p, _ in prices], dataset, want_id)
        sent = {r.meta.subjects[0].entity_id for r, _ in [*rate_rows, *prices]}
        outcome = Outcome(
            counts.recorded - before[0],
            counts.restated - before[1],
            counts.unchanged - before[2],
            tuple(self.status.misses),
        )
        return outcome, sent

    async def check(self) -> dict[str, date | None]:
        """Ask each database for the month before and this one, recording
        nothing; resolve every subject. Each database's latest day stated."""
        done: dict[str, date | None] = {}
        today = self.today()
        for database in DATABASES:
            try:
                read = await self.read(database, month_before(today), today)
            except (PortalUnreachable, NotRead) as failed:
                log.warning("%s was not read: %s", database, failed)
                continue
            done[database] = read.days[-1] if read.days else None
        await self.resolve_pulled()
        misses = self.status.misses
        log.info(
            "checked: %s%s",
            ", ".join(f"{d} to {day}" for d, day in done.items()),
            f"; not held: {', '.join(misses)}" if misses else "",
        )
        return done

    # ── Wants ───────────────────────────────────────────────────────────

    async def on_observations_wanted(
        self, heard: meridian.Heard[ops.ObservationsWantedEvent]
    ) -> None:
        await self.wants.hear(heard, self.answer)

    async def on_want_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        self.wants.withdraw(heard.message.want_id)
        log.info("standing want %s withdrawn", heard.message.want_id)

    def _days(self, want: ops.ObservationsWantedEvent) -> list[date] | None:
        """The days a want asks; None where it asks only the latest."""
        if want.business_date:
            return [date.fromisoformat(want.business_date)]
        if want.valid_from_ns or want.valid_until_ns:
            # Whole seconds, so the last nanosecond before a midnight is
            # that day's, never rounded into the next.
            start = datetime.fromtimestamp(want.valid_from_ns // 10**9, TOKYO).date()
            until = want.valid_until_ns - 1 if want.valid_until_ns else _ns(self.now())
            end = datetime.fromtimestamp(until // 10**9, TOKYO).date()
            span = [start + timedelta(days=n) for n in range((end - start).days + 1)]
            return span[-MOST_DAYS:]
        return None

    async def _held(self, dataset: str) -> set[str]:
        """The subjects `dataset` records, resolved now where not yet."""
        if dataset == FX:
            return {await self.currency(code) for code in CURRENCIES} - {""}
        return {await self.record_of(column.record) for column in RATE_COLUMNS.values()} - {""}

    async def answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        """One want answered from the Bank: its values recorded against it,
        and each subject declined, with why."""
        serves = PRICE if key == FX else RATE
        if key not in KEYS or want.data_type not in ("", serves):
            return {s: "not_covered" for s in subjects}
        if key == FX and kinds and ops.PRICE_KIND_CLOSE not in kinds:
            return {s: "not_covered" for s in subjects}
        held = await self._held(key)
        declined = {s: "not_covered" for s in subjects if s not in held}
        asked = [s for s in subjects if s in held]
        if not asked:
            return declined
        if want.standing:
            self.wants.stand(want, asked, kinds)
        today = self.today()
        days = self._days(want)
        if days is not None:
            days = [d for d in days if d <= today]
        sent: set[str] = set()
        if days is None or days:
            start, end = (min(days), max(days)) if days else (month_before(today), today)
            for database in DATABASES_OF[key]:
                try:
                    read = await self.read(database, start, end)
                except (PortalUnreachable, NotRead) as failed:
                    log.warning("want %s: %s was not read: %s", want.want_id, database, failed)
                    continue
                _, got = await self.record(
                    read,
                    key,
                    want_id=want.want_id,
                    days=days,
                    subjects=set(asked),
                    latest=days is None,
                )
                sent |= got
        for subject in asked:
            if subject not in sent:
                declined[subject] = "source_silent"
        return declined


def _latest(rows: list[tuple[Any, Held]]) -> list[tuple[Any, Held]]:
    """Each subject's rows of its latest day alone."""
    last: dict[str, str] = {}
    for row, _ in rows:
        subject = row.meta.subjects[0].entity_id
        last[subject] = max(last.get(subject, ""), row.meta.business_date)
    return [(r, h) for r, h in rows if r.meta.business_date == last[r.meta.subjects[0].entity_id]]
