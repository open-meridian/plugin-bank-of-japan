# meridian-bank-of-japan

The Bank of Japan's public rates for [Open Meridian](https://open-meridian.com):
an Open Meridian plugin that serves TONA, the call rates, the basic loan rate
and the Tokyo market's exchange rates to a deployment's lake when they are
wanted. It reads BOJ Time-Series Data Search's API, and holds the `data`
role, a data plugin. This is release 0.1.0, a draft for the product owner.
How to set it up and use it is in [docs/](docs/README.md).

It is built on the SDK it pins, `open-meridian==0.37.0` (contract 30).

## What it records

Both datasets are pulled only, when the lake wants a day, and served, not
kept (below).

- **`<instance>:boj_rates`**: the uncollateralized overnight call rate,
  average -- TONA -- a `fixing` with its day's volume in yen (database
  FM01); the collateralized overnight call rate, a `fixing`, and the
  uncollateralized call rates at 1 week, 1, 2 and 3 months, each a `fixing`
  at its tenor on one curve record (FM02); the basic discount rate and basic
  loan rate, a `fixing`, which the Bank states for every calendar day
  (IR01). Actual/365 simple, the plugin's statement: the Bank states
  percent per annum.
- **`<instance>:boj_fx`**: the Tokyo market's spot rates at 17:00 JST, the
  mid of bid and offer (FM08): US dollar/yen, the price of the US dollar's
  cash instrument in yen, and euro/US dollar, the price of the euro's in
  dollars; each a `close`, never inverted.
- **Records:** each is asked of the deployment by the Bank's name for it at
  `boj` (`boj:Call Rate, Uncollateralized Overnight`); the platform seeds
  none yet, so each is reported missing, never minted, and its rates wait.
  The US dollar and the euro resolve by their ISO 4217 codes.
- **Not presented:** the day's highest and lowest call rates and exchange
  rates, the 9:00 JST exchange rates, the central rate, the turnover, the
  Yen Index (calculated with Bloomberg's data, the Bank says), the effective
  exchange rates (FM09) and the monthly series. No published time is
  recorded: the API states none on a value.

## Served, not kept

The Bank's terms ask for its prior permission to copy or reproduce its data
for commercial purposes (ruling 132). So both datasets are read only when
the lake wants a day, nothing the Bank answers is kept in the plugin's
storage -- it declares none -- and no row names a raw record. Each
dataset's terms carry the clause for the deployment admin, whose licence
says whether the lake keeps their rows: served, not kept, until the admin
has recorded the Bank's permission.

## Telling the Bank

The Bank's API notice
([Notice Regarding the Use of the API Service](https://www.stat-search.boj.or.jp/info/api_notice_en.pdf))
asks a service released using the API to notify the Bank's Research and
Statistics Department and to show this credit where the service's users can
find it. That is for the deployment's administrator to do; the plugin sends
nothing to the Bank. The credit reads:

> This service uses the API provided by the "Bank of Japan Time-Series Data
> Search." The Bank of Japan does not guarantee the content of the service.

That is the deployment admin's to do, for the deployment's own service: the
plugin sends nothing to the Bank. The plugin shows the credit on its
Datasets page.

## Deploying it

On a deployment, with the `meridian` CLI connected (`meridian connect`):

    meridian plugin upload                 # from this directory
    meridian plugin launch bank-of-japan   # a deployment admin approves its one role, data

No key and no account. A deployment admin then licenses its two datasets
and entitles the plugins that read them on the Data sources page
([docs/setup.md](docs/setup.md)).

## Checking it

    make ci-local                  # lint, tests, plugin check, image, e2e: the pre-push gate
    make preview SHOTS=<dir>       # each page in a browser with the kit, at 375, 582 and 1280 px

`tests/test_suite.py` runs the SDK's data suite on the plugin's own
conversion, and it passes; a case about what the Bank never states here is
not presented, with why.

## Sample data

The answers committed under `src/bank_of_japan/responses/` are what the
Bank's API answered on 19 November 2026 for October and November 2026 --
its layout, its series' names and units, and the days it stated nothing
for -- with **every value synthetic** (ruling 197): none is the Bank's
figure. The Bank names no column read here as a third party's; the Yen
Index, the one it says is calculated with Bloomberg's data, is not read.

## The terms, summarised

Not legal advice; read the Bank's own words
([notice on the use of the site](https://www.stat-search.boj.or.jp/info/notice_en.html),
[API notice](https://www.stat-search.boj.or.jp/info/api_notice_en.pdf), and
for TONA the
[Terms of Use for the Uncollateralized Overnight Call Rate](https://www.boj.or.jp/en/statistics/outline/exp/data/exmutan2.pdf))
before relying on them. Its data may be copied or reproduced with the Bank
credited, except for commercial purposes, which need the prior permission of
its Research and Statistics Department; its contents may not be altered
without permission; a service using the API is asked to notify the Bank and
show its credit; excessive access is prohibited. Each dataset says so in
words, and declares no licence: the deployment admin's licence is the one
enforced. This project is not affiliated with or endorsed by the Bank of
Japan.

## Licence

Apache-2.0 (LICENSE, NOTICE).
