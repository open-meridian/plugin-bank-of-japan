# Troubleshooting

## Connection

| What you see | What it means | What to do |
|---|---|---|
| **Not answering** | No check has reached the Bank's API | Check the deployment's outbound access to www.stat-search.boj.or.jp; the plugin tries again within the hour |
| **Answering**, with a warning | An earlier check worked; the last did not, or the Bank answered an error (its message ID is shown) | Nothing, usually: the next check runs within the hour. The Bank may limit access under load |

## Records and instruments

| What you see | What it means | What to do |
|---|---|---|
| **N records not held** | Your deployment holds no record for a rate: the platform does not seed them yet | Nothing the plugin can do: it never makes a record. Their values are served once your deployment holds them |
| A currency not resolved | Its ISO 4217 code found no cash instrument, or two | Complete or merge the instrument at the Instruments page |

## Days and subjects

| What you see | What it means | What to do |
|---|---|---|
| A day declined, *source silent* | A weekend, a holiday, a day not published yet; a term rate with no transactions that day | Wait for the Bank's next publication |
| A subject declined, *not covered* | Not one of this plugin's records or currencies | Check the Records tab |

## Licensing

| What you see | What it means | What to do |
|---|---|---|
| Datasets: **Not licensed yet** | No deployment admin has licensed the dataset | Ask a deployment admin to license it on Data sources |
