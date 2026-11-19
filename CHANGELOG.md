# Changelog

## 0.1.0

On open-meridian 0.36.0, contract 30, on core aae501d's harness. The
product owner's items 128, 132, 140 and 175 (2026-11-19): Tier 1, TONA and
the money-market rates, and FX, served, not kept until the deployment admin
records the Bank's permission. The dataset keys, the records' codes and the
source `boj` are proposed here, the product owner's to approve.

- **`boj_rates`** (pull only, served, not kept): TONA (`fixing`, with its
  volume in yen); the collateralized overnight call rate (`fixing`); the
  uncollateralized call rates at 1 week to 3 months (`fixing`s at their
  tenors on one curve record); the basic discount rate and basic loan rate
  (`fixing`). Actual/365 simple, the plugin's statement.
- **`boj_fx`** (pull only, served, not kept): the Tokyo market's US
  dollar/yen and euro/US dollar spot rates at 17:00 JST, each the `close`
  price of one currency's cash instrument in the other, never inverted.
- **The check** asks each database hourly whether the Bank answers, records
  nothing, and resolves every subject; nothing the Bank answers is kept,
  and no storage is declared.
- **No record minted;** no published time.
- **Pages:** the data role's Connection (with Sources) and Datasets (with
  Records), and the credit the Bank's API notice asks for.
- **Sample data:** the Bank's layout and days as answered on 2026-11-19,
  every value synthetic (ruling 197).
