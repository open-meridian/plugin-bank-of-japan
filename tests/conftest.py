"""Shared stand-ins: the Bank of Japan's recorded answers, a fixed clock, the
deployment holding some of the Bank's records and every currency, and the
lake's wants as the sidecar delivers them."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder

from bank_of_japan.feed import Feed
from bank_of_japan.portal import SyntheticPortal

#: After the recording: 22:00 UTC on Thursday 19 November 2026, 07:00 on
#: the 20th in Tokyo.
AT = datetime(2026, 11, 19, 22, 0, tzinfo=UTC)
INSTANCE = "bank-of-japan"
RATES = f"{INSTANCE}:boj_rates"
FX = f"{INSTANCE}:boj_fx"
USD, EUR = "LCL-USD", "LCL-EUR"
#: The records the tests' deployment holds, by their code at `boj`.
HELD = {
    "Call Rate, Uncollateralized Overnight": "INS-TONA",
    "Call Rate, Collateralized Overnight": "INS-COLL",
    "Call Rate, Uncollateralized": "INS-TERM",
    "The Basic Discount Rate and Basic Loan Rate": "INS-BASIC",
}
TONA = HELD["Call Rate, Uncollateralized Overnight"]
TERM = HELD["Call Rate, Uncollateralized"]


def resolving(plugin: Recorder, *left_out: str, ambiguous: str = "") -> Recorder:
    """`plugin` resolving `HELD`'s records but `left_out`, and each ISO code to
    `LCL-<code>` (`ambiguous` to two records)."""

    def resolved(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        named = params.identifiers[0]
        if named.scheme == "iso4217":
            if named.value == ambiguous:
                return ops.ResolveIdentifierResult(
                    found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS
                )
            return ops.ResolveIdentifierResult(found=True, instrument_id=f"LCL-{named.value}")
        found = HELD.get(named.value, "") if named.source == "boj" else ""
        if not found or named.value in left_out:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)
        return ops.ResolveIdentifierResult(found=True, instrument_id=found)

    plugin.answer("ResolveIdentifier", resolved)
    return plugin


def feed(plugin: Recorder | None = None, *, portal: Any = None, at: datetime = AT) -> Feed:
    held = plugin if plugin is not None else resolving(Recorder(INSTANCE))
    return held.bind(Feed(portal or SyntheticPortal(lambda: at), now=lambda: at))


def want(
    want_id: str,
    subjects: list[str],
    *,
    day: str = "",
    standing: bool = False,
    dataset: str = RATES,
    data_type: str = "meridian.v1.Rate",
    kinds: tuple[Any, ...] = (),
) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=dataset,
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            kinds=list(kinds),
            business_date=day,
            standing=standing,
        ),
    )


def fx_want(want_id: str, day: str, subject: str = USD) -> Heard:  # type: ignore[type-arg]
    return want(
        want_id,
        [subject],
        day=day,
        dataset=FX,
        data_type="meridian.v1.Price",
        kinds=(ops.PRICE_KIND_CLOSE,),
    )
