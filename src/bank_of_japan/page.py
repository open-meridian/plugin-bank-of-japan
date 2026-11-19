"""The plugin's pages, under Manage alone: the data role's common pages
(spec/plugin-pages-follow-their-role), Connection and Datasets, in its
order, each also a read tool for agents on the deployment's MCP under the
role's names (`read_connection`, `read_datasets`). Each record is the
role's (`meridian.roles.data`), extended with the Bank of Japan's fields;
each template is the role's, with the Bank's nuance at its blocks only, as
plugin-ecb's are.

A data plugin shows its connectivity, its data subscriptions and how its
entitlements resolve, and no market data (the product owner, 2026-10-03):

- **Connection** (`/`): "Key" -- the mode (Live or Sample data), "No key
  needed", what the Bank serves; "Limits and use" -- the Bank's API notice
  asks for no excessive access, the requests made, the last check and
  error; "Stream": it does not stream. Then a tab of its own
  (`?tab=sources`), **Sources**, one line per database -- FM01, FM02, FM08
  and IR01: its state, the latest day stated, its calls, its last error,
  and in its detail where it reads and that nothing of it is kept.
- **Datasets** (`/datasets`): "Served", "Wants" and "Subjects", each with
  the two datasets; then a tab of its own (`?tab=records`), **Records**:
  each record and currency, with its convention and the deployment's
  instrument for it or why there is none, and each series read and not
  carried -- one line a row, searched and paged by the kit's om-pager to
  fit one screen.

Neither shows a rate or a price: those are the reading roles' to show.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import meridian
from meridian.roles import data

from . import records
from .declared import CATALOGUE, CREDIT
from .feed import Feed, SourceStatus, Status
from .portal import API, BASE
from .series import (
    BASIC_LOAN,
    COLLATERALIZED,
    DATABASES,
    FX,
    FX_COLUMNS,
    NOT_CARRIED,
    RATES,
    TERM,
    TONA,
    dataset_of,
)

TITLE = "Bank of Japan"
#: The kit these pages are built on: 0.12.0's "Facts" and "Next step".
KIT = "0.12.0"

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates", kit=KIT)

CONNECTION = "/"
DATASETS_PAGE = "/datasets"

MOST_QUERY = 100
CONNECTION_TABS = {"connection": "Connection", "sources": "Sources"}
TABS = {"served": "Served", "wants": "Wants", "records": "Records"}
#: The attribution the Bank's terms ask for, and the credit its API notice asks.
ATTRIBUTION = "Source: Bank of Japan. " + CREDIT
SOURCE_NAMES = {
    "FM01": "FM01, the uncollateralized overnight call rate (TONA) and its volume",
    "FM02": "FM02, short-term money market rates: the call rates",
    "FM08": "FM08, foreign exchange rates: the Tokyo market at 17:00 JST",
    "IR01": "IR01, the basic discount rate and basic loan rate",
}
SHORT_NAMES = {
    "FM01": "FM01 TONA",
    "FM02": "FM02 call rates",
    "FM08": "FM08 exchange rates",
    "IR01": "IR01 basic loan rate",
}
KEPT = "Nothing: served, not kept (ruling 132), each answer read and let go"
MONEY = "actual/365, simple: the plugin's statement; the Bank states percent per annum"
#: Each record's dataset, what it is recorded as, and its convention.
RECORDED = {
    TONA.code: (RATES, "fixings, with the day's volume in yen", MONEY),
    COLLATERALIZED.code: (RATES, "fixings", MONEY),
    TERM.code: (RATES, "fixings at 1 week, 1, 2 and 3 months", MONEY),
    BASIC_LOAN.code: (RATES, "fixings, every calendar day, as the Bank states it", MONEY),
}

_held: dict[str, Any] = {}


def hold(feed: Feed) -> None:
    """The feed the pages read, once the plugin has registered."""
    _held["feed"] = feed


def _status() -> tuple[Status, Feed | None]:
    feed: Feed | None = _held.get("feed")
    return (feed.status if feed is not None else Status(), feed)


def _iso(moment: datetime | None) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds") if moment else ""


def _day(day: date | None) -> str:
    return day.isoformat() if day else ""


def _source_state(held: SourceStatus, mode: str) -> str:
    if held.error and held.read_at is None:
        return "Not answering"
    if held.error:
        return "Answering"
    if held.read_at is None:
        return "Checking the Bank"
    return "Sample data" if mode == "synthetic" else "Answering"


def _state(status: Status) -> tuple[str, str, str]:
    """The head's status: its state, what it means, and its detail."""
    error = status.error
    if error and not status.read:
        return "error", "Not answering", error
    if error:
        return "warn", "Answering", error
    if not status.read:
        return "busy", "Checking the Bank", ""
    misses = status.misses
    if misses:
        plural = "record" if len(misses) == 1 else "records"
        more = ", …" if len(misses) > 6 else ""
        return "warn", f"{len(misses)} {plural} not held", ", ".join(sorted(misses)[:6]) + more
    if status.mode == "synthetic":
        return "ok", "Sample data", ""
    return "ok", "Answering", ""


def _source(source: str, status: Status, instance: str) -> records.SourceRead:
    held = status.sources[source]
    return records.SourceRead(
        source=SOURCE_NAMES[source],
        dataset=f"{instance}:{dataset_of(source)}",
        kind=source,
        state=_source_state(held, status.mode),
        last_release=_day(held.latest_day),
        calls=held.fetches,
        last_error=held.error,
        reads=(
            "The answers committed with the plugin: the Bank's layout, synthetic values"
            if status.mode == "synthetic"
            else f"{BASE}{API}, database {source}"
        ),
        history=KEPT,
    )


def connection_read(status: Status, feed: Feed | None) -> records.ConnectionRead:
    state, said, _ = _state(status)
    instance = feed.plugin.identity.instance_id if feed is not None else "bank-of-japan"
    answered = status.read or status.mode == "synthetic"
    return records.ConnectionRead(
        mode="Sample data" if status.mode == "synthetic" else "Live",
        credentials=[],
        entitled_at_vendor=(
            "TONA, the call rates, the basic loan rate and the exchange rates: no key"
            if answered
            else ""
        ),
        limit=(
            "The Bank asks for no excessive access and may limit it under load; the plugin asks "
            "one request at a time, at most one every five seconds, checks each database every "
            "hour, and reads a day only when it is wanted"
        ),
        calls=status.fetches,
        last_call_at=_iso(status.checked_at),
        last_error=status.error,
        sessions=None,
        state=state,
        said=said,
        source=(
            "The answers committed with the plugin: the Bank's layout, synthetic values"
            if status.mode == "synthetic"
            else "BOJ Time-Series Data Search's API"
        ),
        checked_at=_iso(status.checked_at),
        sources=[_source(source, status, instance) for source in DATABASES],
    )


def datasets_read(status: Status, feed: Feed | None) -> records.DatasetsRead:
    instance = feed.plugin.identity.instance_id if feed is not None else "bank-of-japan"
    answered = status.read or status.mode == "synthetic"
    served = data.served(
        CATALOGUE,
        instance,
        feed.wants if feed is not None else None,
        "Yes: no key needed" if answered else "Not asked yet",
    )
    rows = [
        records.RecordRead(
            code=h.code,
            name=h.name,
            dataset=RECORDED[h.code][0],
            recorded_as=RECORDED[h.code][1],
            convention=RECORDED[h.code][2],
            instrument_id=h.instrument_id,
            miss=h.miss,
            latest_day=_day(h.latest_day),
        )
        for h in status.records.values()
    ]
    for series, (code, quoted) in FX_COLUMNS.items():
        held = status.currencies.get(code)
        if held is None or not (held.instrument_id or held.miss):
            continue
        rows.append(
            records.RecordRead(
                code=code,
                name=f"{code} in {quoted} at 17:00 JST, Tokyo market ({series})",
                dataset=FX,
                recorded_as=f"the price of {code} in {quoted}, a close",
                convention=(
                    f"{quoted} per {code}, the mid of bid and offer at 17:00 JST, as the Bank "
                    "states it"
                ),
                instrument_id=held.instrument_id,
                miss=held.miss.replace("_", " "),
                latest_day=_day(held.latest_day),
            )
        )
    rows += [
        records.RecordRead(
            code=held,
            name=why,
            dataset="",
            recorded_as="not carried",
            convention="",
            instrument_id="",
            miss="not carried",
        )
        for held, why in NOT_CARRIED.items()
        if status.records
    ]
    return records.DatasetsRead(
        served=served,
        wants=list(data.want_rows(feed.wants)) if feed is not None else [],
        reads_instruments=True,
        attribution=ATTRIBUTION,
        records=rows,
        unread=[
            f"{line} ({n} reads)"
            for held in status.sources.values()
            for line, n in sorted(held.unread.items())
        ],
    )


def figures(status: Status, feed: Feed | None) -> list[meridian.Figure]:
    """The data role's figures, in its order (`meridian.roles.data`); the
    Bank's plugin reports none of its own."""
    state, said, why = _state(status)
    if status.mode == "synthetic" and state == "ok":
        connection: Any = "Sample data"
    elif said == "Not answering":
        connection = meridian.Figure("", said, state="error", why=why[:200])
    else:
        error = status.error
        connection = meridian.Figure(
            "", "Answering", state="warn" if error else None, why=error[:200]
        )
    last = feed.wants.counts.last_ns if feed is not None else 0
    return data.figures(
        connection=connection,
        entitled_at_vendor=f"{len(CATALOGUE)} of {len(CATALOGUE)} datasets",
        stream="Does not stream",
        last_recorded=(datetime.fromtimestamp(last / 10**9, UTC) if last else None),
    )


def _moment(value: str) -> str:
    """An ISO moment as a person reads it, to the minute in UTC."""
    if not value:
        return ""
    if len(value) == 10:
        return value
    return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _weekday(value: str) -> str:
    return date.fromisoformat(value).strftime("%a %d %b %Y") if value else ""


def matching(query: str, *texts: str) -> bool:
    """Whether every word of a search is in one of `texts`, case aside."""
    words = query.lower().split()
    held = " ".join(texts).lower()
    return all(word in held for word in words)


pages.environment.filters["moment"] = _moment
pages.environment.filters["day"] = _weekday


@pages.page(
    CONNECTION,
    "Connection",
    levels="admin",
    answers=records.ConnectionRead,
    name="read_connection",
    description=(
        "How this plugin reaches the Bank of Japan's Time-Series Data Search API, as every "
        "data plugin's Connection answers it: the mode (Live or Sample data), no key needed, "
        "what the Bank serves, its limits and the requests made, the last check and why it "
        "failed if it did; it does not stream. Then the Bank's own: each database -- FM01, "
        "FM02, FM08 and IR01 -- with its state, the latest day stated, its calls and last "
        "error; nothing of it is kept. No rate."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = connection_read(status, feed)
    tab = request.query.get("tab", "connection")
    return pages.answer(
        "connection.html",
        read,
        detail=_state(status)[2],
        # Named apart from the SDK's own `tab` and `tabs` (0.32.3), which
        # would draw the data role's section row in their place.
        view=tab if tab in CONNECTION_TABS else "connection",
        views=CONNECTION_TABS,
        short=SHORT_NAMES,
    )


@pages.page(
    DATASETS_PAGE,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake, as every data plugin's Datasets answers it: its "
        "two datasets as the catalogue declares them (TONA and the money-market rates; the "
        "Tokyo market's exchange rates, prices; both served, not kept), whether a deployment "
        "admin has licensed each, what it recorded and declined; the standing wants it keeps "
        "and the wants it answered. Then the Bank's own: the credit its terms ask for, and "
        "each record and currency with its convention and the deployment's instrument for it "
        "or why there is none. No rate."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = datasets_read(status, feed)
    # A browser draws one tab, its search narrowing the records drawn; a
    # tool answers every tab.
    query = request.query.get("q", "").strip()[:MOST_QUERY]
    tab = request.query.get("tab", "served")
    tab = "records" if query else tab if tab in TABS else "served"
    shown = [r for r in read.records if matching(query, r.code, r.name, r.dataset)]
    return pages.answer(
        "datasets.html",
        read,
        query=query,
        tab=tab,
        tabs=TABS,
        shown=shown,
        state=_state(status),
        checked_at=_iso(status.checked_at),
    )
