from dataclasses import dataclass
from enum import Enum


@dataclass
class LatLngPoint:
    """A clas to hold information about LatLngPoint"""

    lat: float
    lng: float


@dataclass
class Radius:
    """A class to hold the radius object"""

    value: float
    units: str


@dataclass
class Polygon:
    """A class to hold the polygon object"""

    vertices: list[LatLngPoint]  # A minimum of three LatLngPoints


@dataclass
class Circle:
    """Hold the details of a circle object"""

    center: LatLngPoint
    radius: Radius


@dataclass
class Altitude:
    """A class to hold altitude"""

    value: int | float
    reference: str
    units: str


@dataclass
class Volume3D:
    """A class to hold Volume3D objects"""

    outline_polygon: Polygon
    altitude_lower: Altitude
    altitude_upper: Altitude
    outline_circle: Circle | None = None


@dataclass
class SubscriptionState:
    subscription_id: str
    notification_index: int


@dataclass
class Time:
    """A class to hold time objects"""

    format: str
    value: str


@dataclass
class Volume4D:
    """A class to hold Volume4D objects"""

    volume: Volume3D
    time_start: Time
    time_end: Time


class OperationalIntentState(str, Enum):
    """A test is either pass or fail or could not be processed, currently not"""

    Accepted = "Accepted"
    Activated = "Activated"
    Nonconforming = "Nonconforming"
    Contingent = "Contingent"
