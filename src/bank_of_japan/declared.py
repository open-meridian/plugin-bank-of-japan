"""What this version declares beside its role, `data` (W8.1, W4.1; the
catalogue from contract v18), built from code and used twice: `__main__`
registers with it, and `meridian plugin upload` reads it from the built image
(pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: two datasets** (the product owner, items 128, 132, 140 and
175, 2026-11-19: Tier 1, TONA and the money-market rates, and FX; their keys
proposed, the product owner's to approve):

- **`boj_rates`**: TONA with its volume, the collateralized overnight call
  rate, the uncollateralized call rates at 1 week to 3 months, and the basic
  discount rate and basic loan rate -- rates, daily, from the databases
  FM01, FM02 and IR01;
- **`boj_fx`**: the Tokyo market's US dollar/yen and euro/US dollar spot
  rates at 17:00 JST, each the price of a currency's cash instrument in
  another -- prices, daily, from FM08.

**Served, not kept** (ruling 132, as plugin-fred's `fred_restricted` and
plugin-bank-of-england's curves). The Bank's terms ask for its prior
permission to copy or reproduce its data for commercial purposes. So both
datasets are pulled only, never pushed, and nothing the Bank answers is kept
in the plugin's storage -- it declares none -- and no row names a raw
record; the rows the lake receives are recorded as any are. Whether a
deployment keeps them is its licence: "served, not kept" is the default the
clause in its terms asks the deployment admin to set until the admin has
recorded the Bank's permission (ruling 1032 retired `licence_default`, so
the plugin declares none).

Each: `vendor` the Bank of Japan, no aggregator; `cadence` a day; its day
Tokyo's (the Bank's business day), ending at midnight; no calendar (the
platform holds none for the yen yet); no venue; `history` 0, as each series
states; its terms and pricing (contract 30, ruling 1032) the Bank's, in
plain words, and no licence declared -- a deployment's licence, set on the
Data sources page, is the one enforced; a gap asked again (`gap_recovery`
`backfill`, W10.14).
"""

from __future__ import annotations

from meridian import DatasetDeclaration

from .series import FX, RATES

KEYS = (RATES, FX)
#: The datasets served when wanted and never kept here (ruling 132): both.
NOT_KEPT = KEYS
VENDOR = "Bank of Japan"
RATE = "meridian.v1.Rate"
PRICE = "meridian.v1.Price"
CADENCE = 86_400
DAY_TIME_ZONE = "Asia/Tokyo"
DAY_END_MINUTE = 0

#: The credit the Bank's API notice asks a service using the API to show
#: (https://www.stat-search.boj.or.jp/info/api_notice_en.pdf, II).
CREDIT = (
    'This service uses the API provided by the "Bank of Japan Time-Series Data Search." '
    "The Bank of Japan does not guarantee the content of the service."
)
#: The Bank's terms, in plain words (contract 30, ruling 1032), from its
#: notice on the use of its Time-Series Data Search
#: (https://www.stat-search.boj.or.jp/info/notice_en.html) and its API notice
#: (https://www.stat-search.boj.or.jp/info/api_notice_en.pdf), read on
#: 2026-11-19.
BOJ_TERMS = (
    "The Bank of Japan's Time-Series Data Search and its API: free, no key or account. Its "
    "data may be copied or reproduced with the Bank credited as the source, except for "
    "commercial purposes, which need the prior permission of the Bank's Research and "
    "Statistics Department; its contents may not be altered without the Bank's prior "
    "permission. The Bank's API notice asks a service released using the API to notify the "
    "Research and Statistics Department and to show the credit: " + CREDIT + " Excessive access is prohibited; "
    "the Bank may limit access under load, and suspend or change the API without notice. "
    "Its licence default is served, not kept (ruling 132): the plugin pulls these data only "
    "when wanted and keeps none of them; whether the lake keeps its rows is the deployment "
    "admin's licence to set, once the admin has recorded the Bank's permission. The plugin "
    "notifies the Bank of nothing: that is the deployment's to do."
)
TERMS = {
    RATES: BOJ_TERMS
    + (
        " The uncollateralized overnight call rate is also subject to the Bank's Terms of Use "
        "for it (https://www.boj.or.jp/en/statistics/outline/exp/data/exmutan2.pdf): the Bank "
        "publishes it for general information, does not endorse any instrument referencing "
        "it, and may correct it after publication."
    ),
    FX: BOJ_TERMS + " The Bank says its exchange rates are based on market participants' "
    "information and subject to revision and correction.",
}


def _dataset(key: str, data_types: list[str]) -> DatasetDeclaration:
    return DatasetDeclaration(
        key=key,
        vendor=VENDOR,
        data_types=data_types,
        modes=["pull"],
        cadence=CADENCE,
        history=0,
        terms_and_pricing=TERMS[key],
        gap_recovery="backfill",
        day_time_zone=DAY_TIME_ZONE,
        day_end_minute=DAY_END_MINUTE,
    )


CATALOGUE = [_dataset(RATES, [RATE]), _dataset(FX, [PRICE])]
