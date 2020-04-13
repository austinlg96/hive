from typing import NamedTuple, Tuple, Optional

from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state import vehicle_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_trip import ServicingTrip
from hive.util.exception import SimulationStateError
from hive.model.passenger import board_vehicle
from hive.model.roadnetwork.route import Route, valid_route

from hive.util.typealiases import RequestId, VehicleId

from hive.runner.environment import Environment
from hive.state.vehicle_state import VehicleState


class DispatchTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    request_id: RequestId
    route: Route

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        checks that the request exists and if so, updates the request to know that this vehicle is on it's way
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, or a sim state, or (None, None) if the request isn't there anymore
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request_id)
        if not vehicle:
            error = SimulationStateError(f"vehicle {self.vehicle_id} does not exist")
            return error, None
        elif not request:
            # not an error - may have been picked up. fail silently
            return None, None
        else:
            route_is_valid = valid_route(self.route, vehicle.geoid, request.geoid)
            if not route_is_valid:
                return None, None
            else:
                updated_request = request.assign_dispatched_vehicle(self.vehicle_id, sim.sim_time)
                error, updated_sim = simulation_state_ops.modify_request(sim, updated_request)
                if error:
                    return error, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        this terminates when we reach a base
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        by default, transition to ServicingTrip if possible, else Idle
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request_id)
        if request and request.geoid != vehicle.geoid:
            locations = f"{request.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to request {self.request_id} but locations do not match: {locations}. sim_time: {sim.sim_time}"
            return SimulationStateError(message), None
        elif not request:
            # request already got picked up or was cancelled; go an Idle state
            next_state = Idle(self.vehicle_id)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)
        else:
            # request exists: pick up the trip and enter a ServicingTrip state
            route = sim.road_network.route(request.origin, request.destination)
            # apply next state

            passengers = board_vehicle(request.passengers, self.vehicle_id)
            next_state = ServicingTrip(self.vehicle_id, self.request_id, route, passengers)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        take a step along the route to the base
        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = vehicle_state_ops.move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, move_result.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_state(updated_state)
            return simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)