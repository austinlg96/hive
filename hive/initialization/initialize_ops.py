from typing import Tuple

import yaml
import immutables


def process_fleet_file(fleet_file: str, entity_type: str) -> immutables.Map[str, Tuple[str, ...]]:
    """
    creates an immutable map that contains all of the fleet ids associated with the appropriate entity ids

    :param fleet_file: the file to load memberships from
    :param entity_type: the category the entity falls under, such as vehicles, bases, or stations
    :return: an immutable map mapping all entity ids with the appropriate memberships
    :raises Exception: from KEYErrors parsing the fleets file
        """
    fleet_id_map = immutables.Map()
    fleet_id_map_mutation = fleet_id_map.mutate()

    with open(fleet_file) as f:
        config_dict = yaml.safe_load(f)

        for fleet_id in config_dict:
            for entity_id in config_dict[fleet_id][entity_type]:
                if entity_id in fleet_id_map_mutation:
                    fleet_id_map_mutation[entity_id] = fleet_id_map_mutation[entity_id] + (fleet_id,)
                else:
                    fleet_id_map_mutation.set(entity_id, (fleet_id,))
        fleet_id_map = fleet_id_map_mutation.finish()
    return fleet_id_map
