"""The plugin's settings, declared to the SDK, and what it makes of them.

The Bank of Japan's API needs no key and no choice: the plugin reads it
openly. In the data role's order (spec/plugin-pages-follow-their-role) it
declares no `environment` and no credential ("No key needed"), only the
role's sample data, a developer's setting (`meridian.sample_data`): the
answers committed under responses/ in place of the API, for the e2e and for
trying the plugin offline. It keeps nothing, so it declares no storage and
the SDK declares no storage settings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import meridian

SAMPLE_DATA = "sample_data"


@meridian.settings
class Declared:
    """The settings as declared, in the data role's order."""

    sample_data: bool = meridian.sample_data(
        description=(
            "Serve the answers committed with the plugin instead of asking the Bank of Japan's "
            "API: its layout and its days as the Bank answered on 2026-11-19, to 17 November "
            "2026, every value synthetic. Development deployments only."
        )
    )


DECLARED = Declared


@dataclass(frozen=True)
class Config:
    sample_data: bool = False


def config_from(values: Mapping[str, object]) -> Config:
    """The configuration a delivery of the settings says."""
    return Config(sample_data=values.get(SAMPLE_DATA) is True)
