"""BOJ Time-Series Data Search's API, where the Bank of Japan serves its
statistics, and its stand-in.

One kind of request is made, and nothing else: `getDataCode`, for one
database's series over a range of months, in CSV and in English
(https://www.stat-search.boj.or.jp/info/api_manual_en.pdf, II):

    https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=en
        &db=FM01&code=STRDCLUCON,STRDCLUCV&startDate=202610&endDate=202611

A daily series' range is named by its months, `YYYYMM`. An answer holds at
most 250 series and 60,000 values; one that stops at the limit names the
position to ask from next (`startPosition`), which the plugin asks in turn.
The plugin never comes near it: at most seven series over thirteen months.

Read from the Bank itself: no key, no account. The Bank's API notice
(https://www.stat-search.boj.or.jp/info/api_notice_en.pdf) asks that access
not be excessive and says it may limit access under load; the plugin asks
one request at a time, at most one every five seconds, says who it is in its
User-Agent, and asks for gzip, as the manual recommends. The API sets no
`Last-Modified`, so nothing is asked conditionally.

`SyntheticPortal` answers from the answers committed under responses/
(responses/index.json): each database's series from 1 October to
30 November 2026, as the Bank laid them out on 19 November 2026, every
value synthetic (README, "Sample data"). It answers each request with the
database's whole recording, for the series asked, whatever months are
asked, so the plugin's tests and its e2e run on them, offline, the same on
any day.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib import resources
from typing import Protocol

from .series import DATABASES

BASE = "https://www.stat-search.boj.or.jp"
API = "/api/v1/getDataCode"
USER_AGENT = "meridian-bank-of-japan (+https://github.com/open-meridian/plugin-bank-of-japan)"
SPACING = 5.0
TIMEOUT = 120.0
#: The most an answer may be: a database's seven series over thirteen
#: months are some 0.3 MB.
MOST_BYTES = 16 * 1024 * 1024


def month(day: date) -> str:
    """A day's month, as the API names a daily series' range."""
    return f"{day.year:04d}{day.month:02d}"


def path_for(database: str, codes: Sequence[str], start: date, end: date, position: int = 0) -> str:
    """The request for `codes` of `database` from `start`'s month to `end`'s."""
    query = {
        "format": "csv",
        "lang": "en",
        "db": database,
        "code": ",".join(codes),
        "startDate": month(start),
        "endDate": month(end),
    }
    if position:
        query["startPosition"] = str(position)
    return API + "?" + urllib.parse.urlencode(query, safe=",@")


def asked(path: str) -> tuple[str, list[str]]:
    """The database and series codes a request asks for."""
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
    codes = query.get("code", [""])[0]
    return query.get("db", [""])[0].upper(), [c for c in codes.split(",") if c]


class PortalUnreachable(Exception):  # noqa: N818 - what the Bank's API was
    """The API could not be asked: no answer, or not in time."""


@dataclass(frozen=True)
class Fetched:
    """One answer, as received."""

    path: str
    status: int
    body: bytes
    fetched_at: datetime
    date: str = ""

    @property
    def url(self) -> str:
        return BASE + self.path

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Portal(Protocol):
    mode: str

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class LivePortal:
    """The Bank's API itself."""

    mode = "live"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def get(self, path: str) -> Fetched:
        async with self._lock:
            wait = self._last + SPACING - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                return await asyncio.to_thread(self._get, path)
            finally:
                self._last = time.monotonic()

    def _get(self, path: str) -> Fetched:
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
        request = urllib.request.Request(BASE + path, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - the Bank's https address
                body = answer.read(MOST_BYTES + 1)
                status = answer.status
                said = answer.headers
        except urllib.error.HTTPError as refused:
            body = refused.read(MOST_BYTES + 1) if refused.fp else b""
            status, said = refused.code, refused.headers
        except (urllib.error.URLError, TimeoutError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            raise PortalUnreachable(f"{BASE}{API}: {type(reason).__name__}") from failed
        if len(body) > MOST_BYTES:
            raise PortalUnreachable(f"{BASE}{API}: answered more than {MOST_BYTES} bytes")
        if said is not None and said.get("Content-Encoding", "") == "gzip":
            try:
                body = gzip.decompress(body)
            except (OSError, EOFError) as failed:
                raise PortalUnreachable(f"{BASE}{API}: an answer not gzip") from failed
        return Fetched(path, status, body, self._now(), date=said.get("Date", "") if said else "")


@dataclass(frozen=True)
class Recording:
    """One database's recorded answer: its lines, the Date it was answered
    under, and its last day stated."""

    head: list[str]
    lines: list[str]
    said: str
    last_day: date


class SyntheticPortal:
    """The answers committed under responses/: each database's recording,
    for the series asked, whatever months are asked."""

    mode = "synthetic"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        held = resources.files(__package__).joinpath("responses")
        index = json.loads(held.joinpath("index.json").read_text(encoding="utf-8"))
        self.recordings: dict[str, Recording] = {}
        for database in DATABASES:
            entry = index[database]
            text = held.joinpath(entry["file"]).read_text(encoding="utf-8")
            lines = text.splitlines()
            at = next(i for i, line in enumerate(lines) if line.startswith("SERIES_CODE,"))
            self.recordings[database] = Recording(
                lines[: at + 1],
                lines[at + 1 :],
                str(entry["date"]),
                date.fromisoformat(entry["last_day"]),
            )
        self.asked: list[str] = []

    async def get(self, path: str) -> Fetched:
        self.asked.append(path)
        database, codes = asked(path)
        recording = self.recordings.get(database)
        if recording is None or not path.startswith(API + "?"):
            body = '{"STATUS":400,"MESSAGEID":"M181005E","MESSAGE":"Invalid database name"}'
            return Fetched(
                path, 200, body.encode(), self._now(), recording.said if recording else ""
            )
        known = {line.split(",", 1)[0] for line in recording.lines}
        if not codes or any(c not in known for c in codes):
            body = '{"STATUS":400,"MESSAGEID":"M181013E","MESSAGE":"Nonexistent series code"}'
            return Fetched(path, 200, body.encode(), self._now(), recording.said)
        lines = [line for line in recording.lines if line.split(",", 1)[0] in codes]
        body = "\n".join([*recording.head, *lines]) + "\n"
        return Fetched(path, 200, body.encode(), self._now(), recording.said)


def portal(synthetic: bool, now: Callable[[], datetime] = utc_now) -> Portal:
    return SyntheticPortal(now) if synthetic else LivePortal(now)
