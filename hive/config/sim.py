from __future__ import annotations

from typing import NamedTuple, Dict, Union

from hive.config import ConfigBuilder
from hive.util.typealiases import SimTime


class Sim(NamedTuple):
    timestep_duration_seconds: SimTime
    start_time_seconds: SimTime
    end_time_seconds: SimTime

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'timestep_duration_seconds': 1,  # number of seconds per time step in Hive
            'start_time_seconds': 0,  # 12:00:00am today (range-inclusive value)
            'end_time_seconds': 86400  # 12:00:00am next day (range-exclusive value)
        }

    @classmethod
    def required_config(cls) -> Dict[str, type]:
        return {}

    @classmethod
    def build(cls, config: Dict = None) -> Union[Exception, Sim]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Sim:
        return Sim(
            timestep_duration_seconds=d['timestep_duration_seconds'],
            start_time_seconds=d['start_time_seconds'],
            end_time_seconds=d['end_time_seconds']
        )
