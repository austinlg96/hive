from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, List

from hive.reporting import vehicle_event_ops
from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from hive.config.global_config import GlobalConfig
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report

log = logging.getLogger(__name__)


class EventfulHandler(Handler):
    """
    handles events and appends them to the event.log output file based on global logging settings
    """

    def __init__(self, global_config: GlobalConfig, scenario_output_directory: str):

        log_path = os.path.join(scenario_output_directory, 'event.log')
        self.log_file = open(log_path, 'a')

        self.global_config = global_config

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):

        sim_state = runner_payload.s

        # station load events, written with reference to a specific station, take the sum of
        # charge events over a time step associated with a single station
        if ReportType.STATION_LOAD_EVENT in self.global_config.log_sim_config:
            station_load_reports = vehicle_event_ops.construct_station_load_events(tuple(reports), sim_state)
            for report in station_load_reports:
                entry = json.dumps(report.as_json(), default=str)
                self.log_file.write(entry + '\n')

        for report in reports:
            if report.report_type in self.global_config.log_sim_config:
                entry = json.dumps(report.as_json(), default=str)
                self.log_file.write(entry + '\n')

    def close(self, runner_payload: RunnerPayload):
        self.log_file.close()