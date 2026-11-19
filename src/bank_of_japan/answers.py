"""BOJ Time-Series Data Search's answers to `getDataCode`, read as the Bank
wrote them (its API manual, III, https://www.stat-search.boj.or.jp/info/api_manual_en.pdf).

Asked for CSV in English, an answer is UTF-8: first the processing result
and the parameters, a line each -- `STATUS,200`, `MESSAGEID,M181000I`,
`MESSAGE,...`, `DATE,...` (Japan Standard Time), `PARAMETER,<name>,<value>`
-- and `NEXTPOSITION,` (empty unless the answer stopped at the API's limit,
the position to ask from next); then a header line, `SERIES_CODE,
NAME_OF_TIME_SERIES,UNIT,FREQUENCY,CATEGORY,LAST_UPDATE,SURVEY_DATES,VALUES`,
and one line a series a day, its day as `YYYYMMDD`, its value as the Bank
writes it, `null` where it states none: no value, never a zero.
`M181030I`, "Successfully completed with no applicable data", is an answer
of nulls alone.

An error is answered in JSON whatever was asked: `{"STATUS":400,
"MESSAGEID":"M181013E","MESSAGE":"Nonexistent series code..."}`, 400 for a
request the API refuses, 500 or 503 when it fails; each is `Refused`.

A value is kept as the text the Bank wrote, and read as a `Decimal` from it,
never a float; a value that does not read is kept as not read, and never
recorded.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

MISSING = {"", "null", "NA", "ND"}
HEADER = "SERIES_CODE"


class NotRead(Exception):  # noqa: N818 - what the answer was not
    """An answer that is not what was asked for."""


class Refused(NotRead):
    """An answer the API gave as an error: its status, message ID and message."""

    def __init__(self, status: int, message_id: str, message: str) -> None:
        super().__init__(f"the Bank answered {status} {message_id}: {message[:160]}")
        self.status = status
        self.message_id = message_id


@dataclass(frozen=True)
class Observation:
    """One value as the Bank stated it: its series code, day and text."""

    series: str
    day: date
    text: str

    @property
    def value(self) -> Decimal:
        return Decimal(self.text)


@dataclass
class Table:
    """An answer read: its database, each series' name and unit, its values
    in order, where to ask from next, and the values that did not read."""

    name: str
    message_id: str = ""
    names: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    observations: list[Observation] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)
    next_position: int = 0

    @property
    def days(self) -> list[date]:
        return sorted({o.day for o in self.observations})

    def on(self, day: date) -> dict[str, Observation]:
        return {o.series: o for o in self.observations if o.day == day}

    def extend(self, more: Table) -> None:
        """Another page of the same answer, read on."""
        self.names.update(more.names)
        self.units.update(more.units)
        self.observations = sorted(
            [*self.observations, *more.observations], key=lambda o: (o.series, o.day)
        )
        self.unread += more.unread
        self.next_position = more.next_position


def _number(text: str) -> bool:
    try:
        return Decimal(text).is_finite()
    except InvalidOperation:
        return False


def _refused(text: str) -> Refused:
    try:
        said = json.loads(text)
    except ValueError as failed:
        raise NotRead(f"the answer is neither CSV nor the API's JSON: {text[:80]!r}") from failed
    if not isinstance(said, dict):
        raise NotRead(f"the answer is not the API's JSON: {text[:80]!r}")
    status = said.get("STATUS")
    return Refused(
        status if isinstance(status, int) else 0,
        str(said.get("MESSAGEID", "")),
        str(said.get("MESSAGE", "")),
    )


def parse(text: str, name: str) -> Table:
    """An answer to `getDataCode` for database `name`, read; Refused where
    the API answered an error, NotRead where it is not an answer at all."""
    text = text.lstrip("﻿")
    if text.lstrip().startswith("{"):
        refused = _refused(text)
        if refused.status != 200:
            raise refused
        raise NotRead(f"the answer is JSON, CSV was asked: {text[:80]!r}")
    rows = list(csv.reader(io.StringIO(text)))
    said = {r[0].strip(): r[1:] for r in rows if r and r[0].strip() != HEADER}
    status = said.get("STATUS", [""])[0].strip()
    db = next((r[2].strip() for r in rows if r[:2] == ["PARAMETER", "DB"] and len(r) > 2), "")
    if status != "200" or db.upper() != name:
        raise NotRead(f"the answer is not the Bank's {name}: {text[:80]!r}")
    read = Table(name, message_id=said.get("MESSAGEID", [""])[0].strip())
    position = said.get("NEXTPOSITION", [""])
    read.next_position = int(position[0]) if position and position[0].strip().isdigit() else 0
    at = next((i for i, r in enumerate(rows) if r and r[0].strip() == HEADER), None)
    if at is None:
        if read.message_id == "M181030I":
            return read
        raise NotRead(f"the Bank's {name} answer holds no series: {text[:80]!r}")
    columns = {c.strip(): i for i, c in enumerate(rows[at])}
    if not {"SERIES_CODE", "SURVEY_DATES", "VALUES"} <= set(columns):
        raise NotRead(f"the Bank's {name} answer names no day or value: {rows[at]!r}")

    def cell(row: list[str], key: str) -> str:
        i = columns.get(key)
        return row[i].strip() if i is not None and i < len(row) else ""

    for row in rows[at + 1 :]:
        series = cell(row, "SERIES_CODE")
        if not series:
            continue
        read.names.setdefault(series, cell(row, "NAME_OF_TIME_SERIES"))
        read.units.setdefault(series, cell(row, "UNIT"))
        stated, value = cell(row, "SURVEY_DATES"), cell(row, "VALUES")
        try:
            day = datetime.strptime(stated, "%Y%m%d").date()
        except ValueError:
            read.unread.append(f"{series}: a day {stated[:20]!r}")
            continue
        if value in MISSING:
            continue
        if not _number(value):
            read.unread.append(f"{series} {day}: {value[:40]!r}")
            continue
        read.observations.append(Observation(series, day, value))
    read.observations.sort(key=lambda o: (o.series, o.day))
    return read
