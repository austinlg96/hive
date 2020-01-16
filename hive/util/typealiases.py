from typing import Tuple

# MODEL ID TYPES
RequestId = str
VehicleId = str
StationId = str
PowertrainId = str
PowercurveId = str
BaseId = str
PassengerId = str

# POSITIONAL
GeoId = str  # h3 geohash
LinkId = str # road network link
RouteStepPointer = int
H3Line = Tuple[GeoId, ...]

# TODO: Should we make this datetime so we can freeze and pickup simulations with different requests?
SimTime = int  # time in seconds consistent across inputs (epoch time preferred)
SimStep = int  # the iteration of the simulation
Hours = float  # there's one thing about all of this, we use hours for travel speeds. perhaps change this?
