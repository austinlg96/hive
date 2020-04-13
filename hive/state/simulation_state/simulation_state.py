from __future__ import annotations

from typing import NamedTuple, Optional, cast, Tuple, Callable, TYPE_CHECKING

import immutables
from h3 import h3

from hive.state.simulation_state.at_location_response import AtLocationResponse
from hive.util.exception import SimulationStateError
from hive.util.typealiases import RequestId, VehicleId, BaseId, StationId, SimTime, GeoId

if TYPE_CHECKING:
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.util.units import Seconds
    from hive.model.base import Base
    from hive.model.request import Request
    from hive.model.station import Station
    from hive.model.vehicle import Vehicle


class SimulationState(NamedTuple):
    """
    resolution of '11' is within 25 meters/82 feet. this decides how granular
    the simulation will operate for internal operations. the user can still
    specify their own level of granularity for
    https://uber.github.io/h3/#/documentation/core-library/resolution-table
    """
    # road network representation
    road_network: RoadNetwork

    # simulation parameters
    sim_time: SimTime
    sim_timestep_duration_seconds: Seconds
    sim_h3_location_resolution: int
    sim_h3_search_resolution: int

    # objects of the simulation
    stations: immutables.Map[StationId, Station] = immutables.Map()
    bases: immutables.Map[BaseId, Base] = immutables.Map()
    vehicles: immutables.Map[VehicleId, Vehicle] = immutables.Map()
    requests: immutables.Map[RequestId, Request] = immutables.Map()

    station_iterator: Tuple[StationId, ...] = ()
    base_iterator: Tuple[BaseId, ...] = ()
    vehicle_iterator: Tuple[VehicleId, ...] = ()
    request_iterator: Tuple[RequestId, ...] = ()

    # location collections - the lowest-level spatial representation in Hive
    v_locations: immutables.Map[GeoId, Tuple[VehicleId, ...]] = immutables.Map()
    r_locations: immutables.Map[GeoId, Tuple[RequestId, ...]] = immutables.Map()
    s_locations: immutables.Map[GeoId, StationId] = immutables.Map()
    b_locations: immutables.Map[GeoId, BaseId] = immutables.Map()

    # search collections   - a higher-level spatial representation used for ring search
    v_search: immutables.Map[GeoId, Tuple[VehicleId, ...]] = immutables.Map()
    r_search: immutables.Map[GeoId, Tuple[RequestId, ...]] = immutables.Map()
    s_search: immutables.Map[GeoId, Tuple[StationId, ...]] = immutables.Map()
    b_search: immutables.Map[GeoId, Tuple[BaseId, ...]] = immutables.Map()

    def get_stations(
            self,
            filter_function: Optional[Callable[[Station], bool]] = None,
            sort: bool = False,
            sort_key: Callable = lambda k: k,
            sort_reversed: bool = False,
    ) -> Tuple[Station, ...]:
        """
        returns a tuple of stations.
        users can pass an optional filter and sort function.

        :param filter_function: function to filter results
        :param sort: whether or not to sort the results
        :param sort_key: the key to sort the results by
        :param sort_reversed: the order of the resulting sort
        :return: tuple of sorted and filtered stations
        """
        stations = [self.stations[sid] for sid in self.station_iterator]

        if filter_function and sort:
            return tuple(filter(filter_function, sorted(stations, key=sort_key, reverse=sort_reversed)))
        elif filter_function:
            return tuple(filter(filter_function, stations))
        elif sort:
            return tuple(sorted(stations, key=sort_key, reverse=sort_reversed))
        else:
            return tuple(stations)

    def get_bases(
            self,
            filter_function: Optional[Callable[[Base], bool]] = None,
            sort: bool = False,
            sort_key: Callable = lambda k: k,
            sort_reversed: bool = False,
    ) -> Tuple[Base, ...]:
        """
        returns a tuple of bases.
        users can pass an optional filter and sort function.

        :param filter_function: function to filter results
        :param sort: whether or not to sort the results
        :param sort_key: the key to sort the results by
        :param sort_reversed: the order of the resulting sort
        :return: tuple of sorted and filtered bases
        """
        
        bases = [self.bases[bid] for bid in self.base_iterator]

        if filter_function and sort:
            return tuple(filter(filter_function, sorted(bases, key=sort_key, reverse=sort_reversed)))
        elif filter_function:
            return tuple(filter(filter_function, bases))
        elif sort:
            return tuple(sorted(bases, key=sort_key, reverse=sort_reversed))
        else:
            return tuple(bases)

    def get_vehicles(
            self,
            filter_function: Optional[Callable[[Vehicle], bool]] = None,
            sort: bool = False,
            sort_key: Callable = lambda k: k,
            sort_reversed: bool = False,
    ) -> Tuple[Vehicle, ...]:
        """
        returns a tuple of vehicles.
        users can pass an optional filter and sort function.

        :param filter_function: function to filter results
        :param sort: whether or not to sort the results
        :param sort_key: the key to sort the results by
        :param sort_reversed: the order of the resulting sort
        :return: tuple of sorted and filtered vehicles
        """
        vehicles = [self.vehicles[vid] for vid in self.vehicle_iterator]

        if filter_function and sort:
            return tuple(filter(filter_function, sorted(vehicles, key=sort_key, reverse=sort_reversed)))
        elif filter_function:
            return tuple(filter(filter_function, vehicles))
        elif sort:
            return tuple(sorted(vehicles, key=sort_key, reverse=sort_reversed))
        else:
            return tuple(vehicles) 

    def get_requests(
            self,
            filter_function: Optional[Callable[[Request], bool]] = None,
            sort: bool = False,
            sort_key: Callable = lambda k: k,
            sort_reversed: bool = False,
    ) -> Tuple[Request, ...]:
        """
        returns a tuple of requests.
        users can pass an optional filter and sort function.

        :param filter_function: function to filter results
        :param sort: whether or not to sort the results
        :param sort_key: the key to sort the results by
        :param sort_reversed: the order of the resulting sort
        :return: tuple of sorted and filtered requests
        """
        requests = [self.requests[rid] for rid in self.request_iterator]

        if filter_function and sort:
            return tuple(filter(filter_function, sorted(requests, key=sort_key, reverse=sort_reversed)))
        elif filter_function:
            return tuple(filter(filter_function, requests))
        elif sort:
            return tuple(sorted(requests, key=sort_key, reverse=sort_reversed))
        else:
            return tuple(requests) 

    def at_geoid(self, geoid: GeoId) -> AtLocationResponse:
        """
        returns a dictionary with the list of ids found at this location for all entities
        :param geoid: geoid to look up, should be at the self.sim_h3_location_resolution
        :return: an Optional AtLocationResponse
        """
        vehicles = self.v_locations[geoid] if geoid in self.v_locations else ()
        requests = self.r_locations[geoid] if geoid in self.r_locations else ()
        station = self.s_locations[geoid] if geoid in self.s_locations else None
        base = self.b_locations[geoid] if geoid in self.b_locations else None

        result = cast(AtLocationResponse, {
            'vehicles': vehicles,
            'requests': requests,
            'station': station,
            'base': base
        })
        return result

    def vehicle_at_request(self,
                           vehicle_id: VehicleId,
                           request_id: RequestId,
                           override_resolution: Optional[int] = None) -> bool:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param request_id: the request we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        request = self.requests.get(request_id)
        if not vehicle or not request:
            return False
        else:
            return SimulationState._same_geoid(vehicle.geoid,
                                               request.origin,
                                               self.sim_h3_location_resolution,
                                               override_resolution)

    def vehicle_at_station(self,
                           vehicle_id: VehicleId,
                           station_id: StationId,
                           override_resolution: Optional[int] = None) -> bool:
        """
        tests whether vehicle is at the station within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param station_id: the station we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        station = self.stations.get(station_id)
        if not vehicle or not station:
            return False
        else:
            return SimulationState._same_geoid(vehicle.geoid,
                                               station.geoid,
                                               self.sim_h3_location_resolution,
                                               override_resolution)

    def vehicle_at_base(self,
                        vehicle_id: VehicleId,
                        base_id: BaseId,
                        override_resolution: Optional[int] = None) -> bool:
        """
        tests whether vehicle is at the request within the scope of the given geoid resolution

        :param vehicle_id: the vehicle we are testing for proximity to a request
        :param base_id: the base we are testing for proximity to a vehicle
        :param override_resolution: a resolution to use for geo intersection test; if None, use self.sim_h3_location_resolution
        :return: bool
        """
        vehicle = self.vehicles.get(vehicle_id)
        base = self.bases.get(base_id)
        if not vehicle or not base:
            return False
        else:
            return SimulationState._same_geoid(vehicle.geoid,
                                               base.geoid,
                                               self.sim_h3_location_resolution,
                                               override_resolution)

    @classmethod
    def _same_geoid(cls,
                    a: GeoId,
                    b: GeoId,
                    sim_h3_resolution: int,
                    override_resolution: Optional[int]) -> bool:
        """
        tests if two geoids are the same. allows for overriding test resolution to a parent level
        todo: maybe move this to a geoutility collection somewhere like hive.util._

        :param a: first geoid
        :param b: second geoid
        :param override_resolution: an overriding h3 spatial resolution, or, none to use this sim's default res
        :return: True/False, or, a SimulationStateError
        """
        if override_resolution is None:
            return a == b
        elif override_resolution > sim_h3_resolution:
            error = SimulationStateError(
                f"cannot override geoid resolution {sim_h3_resolution} to smaller hex {override_resolution}")
            return False
        elif override_resolution == sim_h3_resolution:
            return a == b

        a_parent = h3.h3_to_parent(a, override_resolution)
        b_parent = h3.h3_to_parent(b, override_resolution)
        return a_parent == b_parent