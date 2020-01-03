from __future__ import annotations

from typing import NamedTuple, Union

from hive.util.typealiases import LinkId
from hive.model.roadnetwork.link import Link, link_distance
from hive.util.units import unit, km, kmph, h
from hive.util.exception import UnitError


class PropertyLink(NamedTuple):
    """
    a link on the road network which also has road network attributes such as
    distance, speed, and travel time
    """
    link_id: LinkId
    link: Link
    distance: km
    speed: kmph
    travel_time: h

    # grade: float # nice in the future?'

    @classmethod
    def build(cls, link: Link, speed: kmph) -> PropertyLink:
        """
        alternative constructor which sets distance/travel time based on underlying h3 grid
        :param link: the underlying link representation
        :param speed: the speed for traversing the link
        :return: a PropertyLink build around this Link
        """
        assert speed.units == (unit.kilometers / unit.hour), UnitError(
            f"Expected speed in units kmph but got units {speed.units}"
        )
        dist = link_distance(link)
        tt = dist / speed
        return PropertyLink(link.link_id, link, dist, speed, tt)

    @property
    def start(self) -> str:
        return self.link.start

    @property
    def end(self) -> str:
        return self.link.end

    def update_speed(self, speed: kmph) -> PropertyLink:
        assert speed.units == (unit.kilometers / unit.hour), UnitError(
            f"Expected speed in units kmph but got units {speed.units}"
        )
        return self._replace(speed=speed)

    def update_link(self, updated_link: Link) -> Union[AttributeError, PropertyLink]:
        """
        some operations call for updating the the underlying link representation but
        maintaining the properties of the link which are not tied to the link representation.
        :param updated_link: the new Link data
        :return: the updated PropertyLink
        """
        # todo: is it ok to re-calculate distance/travel time here based on h3 distances?
        if self.link_id is not updated_link.link_id:
            return AttributeError(
                f"mismatch: attempting to update PropertyLink {self.link_id} with Link {updated_link.link_id}")
        else:
            dist = link_distance(updated_link)
            tt = dist.magnitude / self.speed.magnitude
            return self._replace(
                link=updated_link,
                distance=dist,
                travel_time=tt * unit.hour
            )

