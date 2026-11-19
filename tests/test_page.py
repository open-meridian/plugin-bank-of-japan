"""The two pages under Manage, and their read tools."""

from __future__ import annotations

import asyncio

import pytest
from meridian.suites import Recorder
from meridian.testing import PageClient

from bank_of_japan import page as page_module
from bank_of_japan.page import CONNECTION, DATASETS_PAGE, figures, hold, pages

from conftest import HELD, INSTANCE, TONA, USD, feed, fx_want, resolving, want


@pytest.fixture
def client() -> PageClient:
    plugin = resolving(Recorder(INSTANCE), "Call Rate, Collateralized Overnight")
    work = feed(plugin)
    asyncio.run(work.check())
    for asked in (fx_want("w-usd", "2026-11-17"), want("w-t", [TONA], day="2026-10-01")):
        plugin.answer("ObservationsWanted", lambda _, w=asked: w.message)  # type: ignore[misc]
        asyncio.run(plugin.hear(work))
    hold(work)
    return PageClient(pages)


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert served == {
        (CONNECTION, "admin"): 200,
        (CONNECTION, "write"): 403,
        (CONNECTION, "read"): 403,
        (DATASETS_PAGE, "admin"): 200,
        (DATASETS_PAGE, "write"): 403,
        (DATASETS_PAGE, "read"): 403,
    }
    client.assert_no_account_data("149.83", "0.477", "20589")


def test_connection_and_its_databases(client: PageClient) -> None:
    text = client.get(CONNECTION, "admin").text
    assert "No key needed" in text and "Does not stream" in text and "1 record not held" in text
    sources = client.get(CONNECTION, "admin", tab="sources").text
    assert sources.count("<tr data-source=") == 4
    assert sources.count("Tue 17 Nov 2026") >= 4
    assert sources.count("served, not kept") == 4


def test_datasets_and_records(client: PageClient) -> None:
    text = client.get(DATASETS_PAGE, "admin").text
    assert all(f"{INSTANCE}:{k}" in text for k in ("boj_rates", "boj_fx"))
    assert "<h2>Wants</h2>" not in text and "<h2>Served</h2>" in text
    assert "Bank of Japan Time-Series Data Search" in text
    wants = client.get(DATASETS_PAGE, "admin", tab="wants").text
    assert "<h2>Wants</h2>" in wants and "<h2>Subjects</h2>" in wants
    records = client.get(DATASETS_PAGE, "admin", tab="records").text
    assert 'data-code="Call Rate, Uncollateralized Overnight"' in records
    assert 'data-code="USD"' in records and 'data-code="EUR"' in records
    assert 'data-code="FXERD39"' in records and "Source: Bank of Japan" in records
    assert client.get(DATASETS_PAGE, "admin", q="FXERD34").text.count("<tr data-code=") == 1


def test_the_tools_answer_what_the_pages_show(client: PageClient) -> None:
    data = client.call_tool("read_connection").data
    assert data["mode"] == "Sample data"
    assert [s["kind"] for s in data["sources"]] == ["FM01", "FM02", "FM08", "IR01"]
    read = client.call_tool("read_datasets").data
    held = {r["code"]: r for r in read["records"]}
    assert held["Call Rate, Uncollateralized Overnight"]["instrument_id"] == TONA
    assert held["Call Rate, Uncollateralized Overnight"]["latest_day"] == "2026-10-01"
    assert held["Call Rate, Collateralized Overnight"]["miss"] == "not held: reported missing"
    assert held["USD"]["dataset"] == "boj_fx" and held["USD"]["instrument_id"] == USD
    assert held["USD"]["latest_day"] == "2026-11-17" and held["EUR"]["latest_day"] == ""
    assert held["FXERD05"]["miss"] == "not carried"
    assert "does not guarantee" in read["attribution"]
    assert HELD


def test_before_the_first_check_and_not_reached() -> None:
    page_module._held.clear()
    assert "Checking the Bank" in PageClient(pages).get(CONNECTION, "admin").text
    work = feed()
    work.status.sources["FM01"].error = "https://www.stat-search.boj.or.jp/api/v1: URLError"
    hold(work)
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert 'state="error"' in text and "Not answering" in text


def test_the_figures_are_the_data_roles(client: PageClient) -> None:
    work = page_module._held["feed"]
    said = figures(work.status, work)
    assert [f.label for f in said][:3] == ["Connection", "Entitled at the vendor", "Stream"]
