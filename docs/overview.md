# Overview

The Bank of Japan publishes the rates this plugin serves your deployment's
lake, through BOJ Time-Series Data Search:

- **Rates** (`<instance>:boj_rates`): the uncollateralized overnight call
  rate, average -- TONA, the yen's risk-free rate -- with its day's volume;
  the collateralized overnight call rate; the uncollateralized call rates at
  1 week, 1, 2 and 3 months; and the basic discount rate and basic loan
  rate.
- **Exchange rates** (`<instance>:boj_fx`): the Tokyo market's US
  dollar/yen and euro/US dollar spot rates at 17:00 JST.

It reads the Bank's public API: no key, no account. Both datasets are read
only when your lake asks for a day, and the plugin keeps nothing the Bank
answers (served, not kept: [terms](terms.md)). Every hour it asks the Bank
whether it answers, recording nothing, so the Connection page says how the
Bank was reached.

## What it records

- **Each value as the Bank writes it,** made an exact decimal from its
  text. A day the Bank states nothing for is no value, never a zero.
- **Conventions.** The Bank states percent per annum; the plugin states
  each rate actual/365 simple, the yen money market's convention. Each
  exchange rate is the mid of bid and offer at 17:00 JST, as the Bank
  states: yen per US dollar, and US dollars per euro.
- **Against your deployment's records.** Each rate's record is asked of
  your deployment by the Bank's name for it at `boj`; the plugin never
  makes a record: one your deployment does not hold is reported missing,
  and its values wait. The US dollar and the euro are found by their ISO
  4217 codes.
- **Revisions.** TONA is published provisionally in the evening and made
  final the next morning; a value read again after the Bank revises it is
  recorded as the same value's next version.
- **No published time:** the API states none on a value.
- **Not carried:** the day's highest and lowest rates, the 9:00 JST rates,
  the central rate, the turnover, the Yen Index, the effective exchange
  rates and the monthly series.

## What it never does

It records no trade and shows no value on its pages. It holds no account,
uses no key, keeps nothing the Bank answers, and notifies the Bank of
nothing. Its exchange rates are never inverted.
