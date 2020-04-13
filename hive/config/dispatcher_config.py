from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple, Optional

from hive.util.units import Ratio, Seconds, Kilometers

from hive.config import ConfigBuilder


class DispatcherConfig(NamedTuple):
    fleet_sizing_update_interval_seconds: Seconds
    matching_low_soc_threshold: Ratio
    charging_low_soc_threshold: Ratio
    charging_max_search_radius_km: Kilometers
    base_vehicles_charging_limit: Optional[int]


    @classmethod
    def default_config(cls) -> Dict:
        return {
            'fleet_sizing_update_interval_seconds': 60 * 15,
            'matching_low_soc_threshold': 0.2,
            'charging_low_soc_threshold': 0.2,
            'charging_max_search_radius_km': 100,
            'base_vehicles_charging_limit': None,
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def build(cls, config: Optional[Dict] = None) -> DispatcherConfig:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: DispatcherConfig.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[IOError, DispatcherConfig]:
        return DispatcherConfig(**d)