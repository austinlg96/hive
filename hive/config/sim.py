from __future__ import annotations

from typing import NamedTuple, Dict, Union, Tuple

from hive.config.config_builder import ConfigBuilder
from hive.util.parsers import time_parser
from hive.util.typealiases import SimTime
from hive.util.units import Seconds


class Sim(NamedTuple):
    sim_name: str
    timestep_duration_seconds: Seconds
    start_time: SimTime
    end_time: SimTime
    sim_h3_resolution: int
    sim_h3_search_resolution: int
    request_cancel_time_seconds: int
    idle_energy_rate: float

    @classmethod
    def default_config(cls) -> Dict:
        return {
            'timestep_duration_seconds': 60,  # number of seconds per time step in Hive
            'sim_h3_resolution': 15,
            'sim_h3_search_resolution': 7,
            'request_cancel_time_seconds': 600,
            'idle_energy_rate': 0.8  # (unit.kilowatthour / unit.hour)
        }

    @classmethod
    def required_config(cls) -> Tuple[str, ...]:
        return (
            'sim_name',
            'start_time',
            'end_time',
        )

    @classmethod
    def build(cls, config: Dict = None) -> Union[IOError, Sim]:
        return ConfigBuilder.build(
            default_config=cls.default_config(),
            required_config=cls.required_config(),
            config_constructor=lambda c: Sim.from_dict(c),
            config=config
        )

    @classmethod
    def from_dict(cls, d: Dict) -> Union[IOError, Sim]:
        start_time = time_parser(d['start_time'])
        if isinstance(start_time, IOError):
            return start_time

        end_time = time_parser(d['end_time'])
        if isinstance(end_time, IOError):
            return end_time

        return Sim(
            sim_name=d['sim_name'],
            timestep_duration_seconds=int(d['timestep_duration_seconds']),
            start_time=start_time,
            end_time=end_time,
            sim_h3_resolution=d['sim_h3_resolution'],
            sim_h3_search_resolution=d['sim_h3_search_resolution'],
            request_cancel_time_seconds=int(d['request_cancel_time_seconds']),
            idle_energy_rate=d['idle_energy_rate'],
        )

    def asdict(self) -> Dict:
        return self._asdict()
