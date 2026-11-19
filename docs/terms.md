# Terms

A summary, not legal advice: read the Bank's own words before relying on
them. Terms change; these were read on 19 November 2026.

From the Bank of Japan's notice on the use of BOJ Time-Series Data Search
([notice](https://www.stat-search.boj.or.jp/info/notice_en.html)):

- **Copying and reproducing** the data is allowed with the Bank credited as
  the source -- **except for commercial purposes,** which need the prior
  permission of the Bank's Research and Statistics Department.
- **No alteration** of the contents without the Bank's prior permission.
- **Revisions.** Figures may be revised retroactively.

From its API notice
([Notice Regarding the Use of the API Service](https://www.stat-search.boj.or.jp/info/api_notice_en.pdf)):

- **Notify the Bank** when releasing a service that uses the API: an e-mail
  to post.rsd17@boj.or.jp, subject "[Release of the service using the API]".
- **Credit:** "This service uses the API provided by the "Bank of Japan
  Time-Series Data Search." The Bank of Japan does not guarantee the content
  of the service.", where the service's users can easily find it.
- **No excessive access.** The Bank may limit access under load, and
  suspend or change the API without notice.

For TONA, the Bank's
[Terms of Use for the Uncollateralized Overnight Call Rate](https://www.boj.or.jp/en/statistics/outline/exp/data/exmutan2.pdf):
the Bank publishes it for general information, endorses no instrument that
references it, does not warrant its accuracy, and may correct it after
publication.

**Served, not kept.** Both datasets are read only when your lake wants a
day, and the plugin keeps nothing the Bank answers. Their terms carry the
clause, and "served, not kept" is the licence default they ask you to set
until you have recorded the Bank's permission.

**Telling the Bank is yours.** The plugin sends nothing to the Bank. If your
deployment releases a service using these data, the notice asks you to
notify the Bank and show its credit; the plugin shows the credit on its
Datasets page.

Each dataset describes these terms in words, shown on the Data sources
page, and declares no licence. The licence a deployment admin sets there is
the one enforced; the plugin says nothing of whether your deployment meets
anyone's terms.

This project is not affiliated with or endorsed by the Bank of Japan.
