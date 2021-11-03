from __future__ import annotations

import csv
import functools as ft
import logging
from pathlib import Path
from typing import Tuple, Dict

import immutables

from hive.config import HiveConfig
from hive.initialization.initialize_ops import process_fleet_file, read_fleet_ids_from_file
from hive.model.base import Base
from hive.model.energy.charger import build_chargers_table
from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork
from hive.model.station import Station
from hive.model.vehicle.mechatronics import build_mechatronics_table
from hive.model.vehicle.schedules import build_schedules_table
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.handler.eventful_handler import EventfulHandler
from hive.reporting.handler.instruction_handler import InstructionHandler
from hive.reporting.handler.stateful_handler import StatefulHandler
from hive.reporting.handler.stats_handler import StatsHandler
from hive.reporting.reporter import Reporter
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util import DictOps

log = logging.getLogger(__name__)


def initialize_simulation(
        config: HiveConfig,
) -> Tuple[SimulationState, Environment]:
    """
    constructs a SimulationState from sets of vehicles, stations, and bases, along with a road network

    :param config: the configuration of this run
    :return: a SimulationState, or a SimulationStateError
    :raises Exception due to IOErrors, missing keys in DictReader rows, or parsing errors
    """

    # deprecated geofence input
    if config.input_config.geofence_file:
        geofence = GeoFence.from_geojson_file(config.input_config.geofence_file)
    else:
        geofence = None

    # set up road network based on user-configured road network type
    if config.network.network_type == 'euclidean':
        road_network = HaversineRoadNetwork(geofence=geofence, sim_h3_resolution=config.sim.sim_h3_resolution)
    elif config.network.network_type == 'osm_network':
        road_network = OSMRoadNetwork(
            geofence=geofence,
            sim_h3_resolution=config.sim.sim_h3_resolution,
            road_network_file=Path(config.input_config.road_network_file),
            default_speed_kmph=config.network.default_speed_kmph,
        )
    else:
        raise IOError(
            f"road network type {config.network.network_type} not valid, must be one of {{euclidean|osm_network}}")

    # initial sim state with road network and no entities
    sim_initial = SimulationState(
        road_network=road_network,
        sim_time=config.sim.start_time,
        sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
        sim_h3_location_resolution=config.sim.sim_h3_resolution,
        sim_h3_search_resolution=config.sim.sim_h3_search_resolution
    )

    # create simulation environment
    fleet_ids = read_fleet_ids_from_file(config.input_config.fleets_file) if config.input_config.fleets_file else []

    # read in fleet memberships for vehicles/stations/bases
    vehicle_member_ids = process_fleet_file(config.input_config.fleets_file,
                                            'vehicles') if config.input_config.fleets_file else None
    base_member_ids = process_fleet_file(config.input_config.fleets_file,
                                         'bases') if config.input_config.fleets_file else None
    station_member_ids = process_fleet_file(config.input_config.fleets_file,
                                            'stations') if config.input_config.fleets_file else None

    env_initial = Environment(config=config,
                              mechatronics=build_mechatronics_table(config.input_config.mechatronics_file,
                                                                    config.input_config.scenario_directory),
                              chargers=build_chargers_table(config.input_config.chargers_file),
                              schedules=build_schedules_table(config.sim.schedule_type,
                                                              config.input_config.schedules_file),
                              fleet_ids=fleet_ids,
                              )

    # populate simulation with entities
    sim_with_vehicles, env_updated = _build_vehicles(config.input_config.vehicles_file, vehicle_member_ids, sim_initial,
                                                     env_initial)
    sim_with_bases = _build_bases(config.input_config.bases_file, base_member_ids, sim_with_vehicles)
    sim_with_stations = _build_stations(config.input_config.stations_file, station_member_ids, sim_with_bases)
    sim_with_home_bases = _assign_private_memberships(sim_with_stations)

    return sim_with_home_bases, env_updated


def _build_vehicles(
        vehicles_file: str,
        vehicle_member_ids: immutables.Map[str, Tuple[str, ...]],
        simulation_state: SimulationState,
        environment: Environment) -> Tuple[SimulationState, Environment]:
    """
    adds all vehicles from the provided vehicles file

    :param vehicles_file: the file to load vehicles from
    :param vehicle_member_ids: an immutables Map with all of the vehicle membership ids
    :param simulation_state: the partially-constructed simulation state
    :param environment: the partially-constructed environment
    :return: the SimulationState with vehicles in it
    :raises Exception: from IOErrors parsing the vehicle, powertrain, or powercurve files
    """

    def _add_row_unsafe(
            payload: Tuple[SimulationState, Environment],
            row: Dict[str, str]) -> Tuple[SimulationState, Environment]:

        sim, env = payload
        veh = Vehicle.from_row(row, sim.road_network, env)
        if vehicle_member_ids is not None:
            if veh.id in vehicle_member_ids:
                veh = veh.set_membership(vehicle_member_ids[veh.id])
        error, updated_sim = simulation_state_ops.add_vehicle(sim, veh)
        if error:
            log.error(error)
            return sim, env
        else:
            return updated_sim, env

    # open vehicles file and add each row
    with open(vehicles_file, 'r', encoding='utf-8-sig') as vf:
        reader = csv.DictReader(vf)
        initial_payload = simulation_state, environment
        sim_with_vehicles = ft.reduce(_add_row_unsafe, reader, initial_payload)
    return sim_with_vehicles


def _build_bases(bases_file: str,
                 base_member_ids: immutables.Map[str, Tuple[str, ...]],
                 simulation_state: SimulationState,
                 ) -> SimulationState:
    """
    all your base are belong to us

    :param bases_file: path to file with bases
    :param base_member_ids: an immutables Map with all of the base membership ids
    :param simulation_state: the partial simulation state
    :return: the simulation state with all bases in it
    :raises Exception if a parse error in Base.from_row or any error adding the Base to the Sim
    """

    def _add_row_unsafe(sim: SimulationState, row: Dict[str, str]) -> SimulationState:
        base = Base.from_row(row, simulation_state.road_network)
        if base_member_ids is not None:
            if base.id in base_member_ids:
                base = base.set_membership(base_member_ids[base.id])
        error, updated_sim = simulation_state_ops.add_base(sim, base)
        if error:
            log.error(error)
            return sim
        else:
            return updated_sim

    # add all bases from the base file
    with open(bases_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        sim_with_bases = ft.reduce(_add_row_unsafe, reader, simulation_state)

    return sim_with_bases


def _assign_private_memberships(sim: SimulationState) -> SimulationState:
    """
    vehicles which had a home base assigned will automatically generate a home base membership id
    which links the vehicle and the base, in order to avoid having to specify this (obvious) relationship
    in the fleets configuration of a scenario.

    :param sim: partial simulation state with vehicles and bases added
    :return: sim state where vehicles + bases which should have a private relationship have been updated
    """

    def _find_human_drivers(acc: SimulationState, v: Vehicle) -> SimulationState:
        home_base_id = v.driver_state.home_base_id
        if home_base_id is None:
            return acc
        else:
            home_base = sim.bases.get(home_base_id)
            if not home_base:
                log.error(f"home base {home_base_id} does not exist but is listed as home base for vehicle {v.id}")
                return acc
            else:
                home_base_membership_id = f"{v.id}_private_{home_base_id}"
                updated_v = v.add_membership(home_base_membership_id)
                updated_b = home_base.add_membership(home_base_membership_id)
                station = sim.stations.get(home_base.station_id)
                updated_s = station.add_membership(home_base_membership_id) if station else None

                error_v, with_v = simulation_state_ops.modify_vehicle(acc, updated_v)
                if error_v:
                    log.error(error_v)
                    return acc
                else:
                    error_b, with_b = simulation_state_ops.modify_base(with_v, updated_b)
                    if error_b:
                        log.error(error_b)
                        return acc
                    else:
                        # bases are not required to have stations (they are optional)
                        if not station:
                            return with_b
                        else:
                            error_s, with_s = simulation_state_ops.modify_station(with_b, updated_s)
                            if error_s:
                                log.error(error_s)
                                return acc
                            else:
                                return with_s

    result = ft.reduce(
        _find_human_drivers,
        sim.get_vehicles(),
        sim
    )
    return result


def _build_stations(stations_file: str,
                    station_member_ids: immutables.Map[str, Tuple[str, ...]],
                    simulation_state: SimulationState,
                    ) -> SimulationState:
    """
    all your station are belong to us

    :param stations_file: the file with stations in it
    :param station_member_ids: an immutables Map with all of the station membership ids
    :param simulation_state: the partial simulation state
    :return: the resulting simulation state with all stations in it
    :raises Exception if parsing a Station row failed or adding a Station to the Simulation failed
    """

    def _add_row_unsafe(builder: immutables.Map[str, Station], row: Dict[str, str]) -> immutables.Map[str, Station]:
        station = Station.from_row(row, builder, simulation_state.road_network)
        updated_builder = DictOps.add_to_dict(builder, station.id, station)
        return updated_builder

    def _add_station_unsafe(sim: SimulationState, station: Station) -> SimulationState:
        if station_member_ids is not None:
            if station.id in station_member_ids:
                station = station.set_membership(station_member_ids[station.id])
        error, sim_with_station = simulation_state_ops.add_station(sim, station)
        if error:
            log.error(error)
            return sim
        else:
            return sim_with_station

    # grab all stations (some may exist on multiple rows)
    with open(stations_file, 'r', encoding='utf-8-sig') as bf:
        reader = csv.DictReader(bf)
        stations_builder = ft.reduce(_add_row_unsafe, reader, immutables.Map())

    # add all stations to the simulation once we know they are complete
    sim_with_stations = ft.reduce(_add_station_unsafe, stations_builder.values(), simulation_state)

    return sim_with_stations
