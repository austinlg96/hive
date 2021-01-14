from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Callable

import h3

from hive.model.roadnetwork.geofence import GeoFence
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.route import Route
from hive.model.sim_time import SimTime
from hive.util.typealiases import GeoId, H3Resolution
from hive.util.units import Kilometers


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    sim_h3_resolution: H3Resolution
    geofence: Optional[GeoFence]

    @abstractmethod
    def route(self, origin: Link, destination: Link) -> Route:
        """
        Returns a route between two road network property links


        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: A route.
        """

    @abstractmethod
    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        """
        Returns the road network distance between two geoids


        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: the distance in kilometers.
        """

    @abstractmethod
    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        finds the nearest link to a given GeoId

        :param geoid: a physical location
        :return: The nearest road network link to the provided GeoId
        """

    def stationary_location_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        creates a Link which represents a fixed location on the road network for
        stationary entities such as Requests, Stations, and Bases.
        if the provided GeoId does not exist on the line of GeoIds coincident with this Link,
        then the nearest one is
        :param geoid: the location for the stationary entity
        :return: the nearest Link to the GeoId, with start/end locations modified to match
        the stationary location
        """
        link = self.link_from_geoid(geoid)
        if not link:
            return None
        else:
            hexes_on_link = h3.h3_line(link.start, link.end)
            if geoid in hexes_on_link:
                updated = link.update_start(geoid).update_end(geoid)
                return updated
            else:
                hexes_by_dist = sorted(hexes_on_link, key=lambda h: h3.h3_distance(geoid, h))
                closest_hex_to_query = hexes_by_dist[0]
                updated = link.update_start(closest_hex_to_query).update_end(closest_hex_to_query)
                return updated

    @abstractmethod
    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance


        :param geoid: an h3 geoid
        :return: True/False
        """

    @abstractmethod
    def update(self, sim_time: SimTime) -> RoadNetwork:
        """
        requests an update to the road network state to refect the provided simulation time

        :param sim_time:
        :return:
        """

