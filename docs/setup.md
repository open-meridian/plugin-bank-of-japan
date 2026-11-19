# Setup

## Launching it

The Bank of Japan's data need no key and no account. Launch the plugin and
approve its one role, `data`. It asks the Bank at once, and every hour
after, recording nothing; it reads a day only when the lake asks for it.

Its one setting, on a deployment installed for development: **Sample
data**, the Bank's layout and days as its API answered on 19 November 2026,
committed with the plugin, every value synthetic.

## Telling the Bank

The Bank's API notice asks whoever releases a service using its API to
notify its Research and Statistics Department by e-mail
(post.rsd17@boj.or.jp, subject "[Release of the service using the API]"),
and to show its credit where the service's users can find it ([terms](terms.md)).
If your deployment serves these data to anyone, that is yours to do: the
plugin sends nothing to the Bank.

## Its datasets

On the deployment's **Data sources** page (deployment admins), for each of
`<instance>:boj_rates` and `<instance>:boj_fx`:

1. **License it.** Each dataset describes the Bank's terms in words and
   declares no licence ([terms](terms.md)). Each carries the clause "served,
   not kept": the Bank's prior permission is needed to copy or reproduce its
   data for commercial purposes, so the plugin reads them only when wanted
   and keeps none of them; set the licence not to keep them until you have
   recorded the Bank's permission. Until a licence is set, the lake keeps
   the rows and reads every use right restrictively.
2. **Entitle** each plugin that reads it.
3. **Priority**, where another dataset states the same values.

## The records

Each rate is about a record named by the Bank's name for it at `boj`:
`boj:Call Rate, Uncollateralized Overnight` (TONA),
`boj:Call Rate, Collateralized Overnight`, `boj:Call Rate, Uncollateralized`
(the term rates' curve) and `boj:The Basic Discount Rate and Basic Loan Rate`.
The platform does not seed them yet, and the plugin never makes one: the
Datasets page's Records tab shows each as not held, and its values wait
until your deployment holds it. The US dollar and the euro are found by
their ISO 4217 codes.
