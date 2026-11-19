"""The catalogue, from code, as the deployment approves it."""

from __future__ import annotations

from meridian.plugin.v1 import operations_pb2 as ops

from bank_of_japan.declaration import DECLARATION


def test_two_datasets_rates_and_prices() -> None:
    keys = [d.key for d in DECLARATION.catalogue]
    assert keys == ["boj_rates", "boj_fx"]
    kinds = {d.key: list(d.data_types) for d in DECLARATION.catalogue}
    assert kinds == {"boj_rates": ["meridian.v1.Rate"], "boj_fx": ["meridian.v1.Price"]}
    for dataset in DECLARATION.catalogue:
        assert dataset.day_time_zone == "Asia/Tokyo" and dataset.vendor == "Bank of Japan"
        assert dataset.gap_recovery == "backfill" and not dataset.calendar_id
        said = dataset.terms_and_pricing
        assert "commercial purposes" in said and "post.rsd17@boj.or.jp" in said
        assert "Bank of Japan Time-Series Data Search" in said and len(said) <= 2000


def test_both_are_pulled_only_and_served_not_kept() -> None:
    for dataset in DECLARATION.catalogue:
        assert list(dataset.modes) == [ops.OBSERVATION_MODE_PULL]
        assert "served, not kept" in dataset.terms_and_pricing


def test_nothing_is_kept_so_no_storage_is_declared() -> None:
    assert DECLARATION.storage is None
