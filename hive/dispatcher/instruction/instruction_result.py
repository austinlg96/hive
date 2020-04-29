from typing import NamedTuple

from hive.state.vehicle_state import VehicleState


class InstructionResult(NamedTuple):
    prev_state: VehicleState
    next_state: VehicleState
