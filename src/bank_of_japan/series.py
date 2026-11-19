"""The Bank of Japan's series this version carries, what each one is, and
the record it is recorded against: the plugin's series map.

The Bank publishes its statistics through BOJ Time-Series Data Search,
whose API (https://www.stat-search.boj.or.jp/info/api_manual_en.pdf) answers
`getDataCode` for one database at a time, each series named by its series
code and stating its own name, unit and frequency. Four databases are read,
and in each only the series named here.

**Rates** (`boj_rates`), each in "percent per annum", as the Bank states
them:

- FM01, the uncollateralized overnight call rate, average (`STRDCLUCON`):
  the Tokyo Overnight Average Rate (TONA), the yen's risk-free rate, a
  `fixing`, with its day's volume (`STRDCLUCV`, "100 million yen", recorded
  in yen);
- FM02, the collateralized overnight call rate (`STRDCLCOON`), a `fixing`;
  and the uncollateralized call rates at 1 week, 1 month, 2 months and
  3 months (`STRDCLUC1W` to `STRDCLUC3M`), each a `fixing` at its tenor on
  one `rate_curve` record;
- IR01, the basic discount rate and basic loan rate (`MADR1Z@D`), a
  `fixing`, stated by the Bank for every calendar day.

Actual/365 simple: the yen money market's convention, which the Bank
states on none of these series -- the plugin's statement. Each call rate is
the Bank's volume-weighted average of the transactions its information
providers (three money market brokers) submit, rounded to three decimal
places (the Bank's "Explanation of 'Statistics on Call Money Market'",
https://www.boj.or.jp/en/statistics/outline/exp/exmenu_m.pdf).

**FX** (`boj_fx`, FM08): the Tokyo market's spot rates at 17:00 JST, "the
mid rates of the bid and offer rates" (the Bank's Foreign Exchange Rates
page, https://www.boj.or.jp/en/statistics/market/forex/fxdaily/index.htm):
US dollar/yen (`FXERD04`), "Yen per U.S. Dollar", the price of the US
dollar's cash instrument in yen; and euro/US dollar (`FXERD34`), "U.S.
Dollar per Euro", the price of the euro's cash instrument in dollars. Each
a `close`, never inverted.

**Not carried**, and why, in `NOT_CARRIED`: the day's highest and lowest
rates, the 9:00 JST rates, the central rate, the turnover, and the Yen
Index, which the Bank's daily release says is calculated with Bloomberg's
data.

Each record is asked of the deployment by the Bank's own name for it as a
`symbol` at the source `boj`, a name **proposed** with this version for
the platform's seed; the platform seeds none yet, so until a deployment
holds a record its values wait, reported missing, never minted. The US
dollar and the euro are resolved by their ISO 4217 codes, as plugin-ecb
resolves its currencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from meridian.operations import RateConvention

SOURCE = "boj"
INTEREST_RATE, RATE_CURVE = "interest_rate", "rate_curve"
#: The databases read, by the Bank's DB name.
FM01, FM02, FM08, IR01 = "FM01", "FM02", "FM08", "IR01"
DATABASES = (FM01, FM02, FM08, IR01)
#: The datasets, as declared.py names them.
RATES, FX = "boj_rates", "boj_fx"

#: The yen money market's convention.
MONEY_MARKET_365 = RateConvention(day_count="act_365_fixed", compounding="simple")
#: The yen, the currency TONA's volume is stated in.
JPY = "JPY"
#: "100 million yen", the unit of TONA's volume.
VOLUME_UNIT = 100_000_000


@dataclass(frozen=True)
class Record:
    """A referential record, by the code proposed for it at `boj`."""

    code: str
    instrument_type: str
    description: str

    @property
    def identifier(self) -> tuple[str, str, str]:
        return ("symbol", self.code, SOURCE)


TONA = Record(
    "Call Rate, Uncollateralized Overnight",
    INTEREST_RATE,
    "Tokyo Overnight Average Rate (TONA): the Bank of Japan's uncollateralized overnight "
    "call rate, average",
)
COLLATERALIZED = Record(
    "Call Rate, Collateralized Overnight",
    INTEREST_RATE,
    "The Bank of Japan's collateralized overnight call rate",
)
TERM = Record(
    "Call Rate, Uncollateralized",
    RATE_CURVE,
    "The Bank of Japan's uncollateralized call rates, 1 week to 3 months",
)
BASIC_LOAN = Record(
    "The Basic Discount Rate and Basic Loan Rate",
    INTEREST_RATE,
    "The Bank of Japan's basic discount rate and basic loan rate",
)
RECORDS = (TONA, COLLATERALIZED, TERM, BASIC_LOAN)


@dataclass(frozen=True)
class Column:
    """A series carried: its database, record, kind and tenor."""

    database: str
    record: Record
    kind: str = "fixing"
    tenor: str = ""
    convention: RateConvention = MONEY_MARKET_365


#: The rate series carried, by series code.
RATE_COLUMNS: dict[str, Column] = {
    "STRDCLUCON": Column(FM01, TONA),
    "STRDCLCOON": Column(FM02, COLLATERALIZED),
    "STRDCLUC1W": Column(FM02, TERM, tenor="1W"),
    "STRDCLUC1M": Column(FM02, TERM, tenor="1M"),
    "STRDCLUC2M": Column(FM02, TERM, tenor="2M"),
    "STRDCLUC3M": Column(FM02, TERM, tenor="3M"),
    "MADR1Z@D": Column(IR01, BASIC_LOAN),
}
#: TONA's volume, "100 million yen", by series code.
VOLUME = "STRDCLUCV"

#: The exchange rates carried: each series code's currency priced, and the
#: currency it is priced in.
FX_COLUMNS: dict[str, tuple[str, str]] = {
    "FXERD04": ("USD", JPY),
    "FXERD34": ("EUR", "USD"),
}
#: The currencies priced, each resolved by its ISO 4217 code.
CURRENCIES = ("USD", "EUR")

#: The series each database is asked for.
CODES = {
    database: tuple(
        [s for s, c in RATE_COLUMNS.items() if c.database == database]
        + ([VOLUME] if database == FM01 else [])
        + ([*FX_COLUMNS] if database == FM08 else [])
    )
    for database in DATABASES
}
#: Each dataset's databases.
DATABASES_OF = {RATES: (FM01, FM02, IR01), FX: (FM08,)}

#: What the databases read hold and are not carried, and why.
NOT_CARRIED = {
    "STRDCLUCONH": "the highest uncollateralized overnight rate of the day: not a fixing",
    "STRDCLUCONL": "the lowest uncollateralized overnight rate of the day: not a fixing",
    "FXERD01": "US dollar/yen at 9:00 JST: the day's rate at 17:00 is recorded as its close",
    "FXERD31": "euro/US dollar at 9:00 JST: the day's rate at 17:00 is recorded as its close",
    "FXERD02": "US dollar/yen, the day's highest: not a close",
    "FXERD03": "US dollar/yen, the day's lowest: not a close",
    "FXERD05": "US dollar/yen central rate, the day's most traded rate: no price kind says it",
    "FXERD06": "US dollar/yen spot turnover, via brokers: a volume, not a price",
    "FXERD39": "the Yen Index: an index, calculated with Bloomberg's data, the Bank says",
}


def dataset_of(database: str) -> str:
    """A database's dataset."""
    return FX if database == FM08 else RATES
