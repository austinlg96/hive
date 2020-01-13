from __future__ import annotations

import functools as ft
from typing import NamedTuple
from typing import Optional, Union

from hive.model.roadnetwork.linktraversal import LinkTraversal
from hive.model.roadnetwork.linktraversal import traverse_up_to
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.route import Route
from hive.util.helpers import TupleOps
from hive.util.typealiases import *
from hive.util.units import unit, h, s, km


class RouteTraversal(NamedTuple):
    """
    A tuple that represents the result of traversing a route.

    :param remaining_time: The (estimated) time remaining in the route.
    :type remaining_time: :py:obj:`hours`
    :param travel_distance: The distance of the experienced route.
    :type travel_distance: :py:obj:`kilometers`
    :param experienced_route: The route that was traversed during a traversal.
    :type experienced_route: :py:obj:`Route`
    :param remaining_route: The route that remains after a traversal.
    :type remaining_route: :py:obj:`Route`
    """
    remaining_time: h = 0 * unit.hours
    traversal_distance: km = 0 * unit.kilometers
    experienced_route: Route = ()
    remaining_route: Route = ()

    def no_time_left(self):
        """
        if we have no more time, then end the traversal

        :return: True if the agent is out of time
        """
        return self.remaining_time.magnitude == 0

    def add_traversal(self, t: LinkTraversal) -> RouteTraversal:
        """
        take the result of a link traversal and update the route traversal

        :param t: a link traversal
        :return: the updated route traversal
        """
        updated_experienced_route = self.experienced_route \
            if t.traversed is None \
            else self.experienced_route + (t.traversed,)
        updated_remaining_route = self.remaining_route \
            if t.remaining is None \
            else self.remaining_route + (t.remaining,)
        if t.traversed:
            traversal_distance = self.traversal_distance + t.traversed.distance
        else:
            traversal_distance = self.traversal_distance
        return self._replace(
            remaining_time=t.remaining_time,
            traversal_distance= traversal_distance,
            experienced_route=updated_experienced_route,
            remaining_route=updated_remaining_route,
        )

    def add_link_not_traversed(self, link: PropertyLink) -> RouteTraversal:
        """
        if a link wasn't traversed, be sure to add it to the remaining route

        :param link: a link for the remaining route
        :return: the updated RouteTraversal
        """
        return self._replace(
            remaining_route=self.remaining_route + (link,)
        )


def traverse(route_estimate: Route,
             road_network: RoadNetwork,
             time_step: s) -> Optional[Union[Exception, RouteTraversal]]:
    """
    step through the route from the current agent position (assumed to be start.link_id) toward the destination

    :param route_estimate: the current route estimate
    :param road_network: the current road network state
    :param time_step: size of the time step for this traversal
    :return: a route experience and updated route estimate;
             or, nothing if the route is consumed.
             an exception is possible if the current step is not found on the link or
             the route is malformed.
    """
    if len(route_estimate) == 0:
        return None
    elif TupleOps.head(route_estimate).start == TupleOps.last(route_estimate).end:
        return None
    else:

        # function that steps through the route
        def _traverse(acc: Tuple[RouteTraversal, Optional[Exception]],
                      property_link: PropertyLink) -> Tuple[RouteTraversal, Optional[Exception]]:
            acc_traversal, acc_failures = acc
            if acc_traversal.no_time_left():
                return acc_traversal.add_link_not_traversed(property_link), acc_failures
            else:
                # traverse this link as far as we can go
                traverse_result = traverse_up_to(road_network, property_link, acc_traversal.remaining_time)
                if isinstance(traverse_result, Exception):
                    return acc_traversal, traverse_result
                else:
                    updated_experienced_route = acc_traversal.add_traversal(traverse_result)
                    return updated_experienced_route, acc_failures

        # initial search state has a route traversal and an Optional[Exception]
        initial = (RouteTraversal(remaining_time=time_step.to(unit.hours)), None)

        traversal_result, error = ft.reduce(
            _traverse,
            route_estimate,
            initial
        )

        if error is not None:
            return error
        else:
            return traversal_result