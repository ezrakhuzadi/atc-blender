from dataclasses import dataclass, field
from enum import Enum

from common.geo_types import (
    Altitude,
    Circle,
    LatLngPoint,
    OperationalIntentState,
    Polygon,
    Radius,
    SubscriptionState,
    Time,
    Volume3D,
    Volume4D,
)
from rid_operations.rid_utils import RIDFlightDetails
from scd_operations.scd_data_definitions import (
    OperationalIntentDetailsUSSResponse,
    OperationalIntentReferenceDSSResponse,
    OperationalIntentUSSDetails,
)


@dataclass
class OperationalIntentNotFoundResponse:
    message: str


@dataclass
class UpdateOperationalIntent:
    message: str


@dataclass
class GenericErrorResponseMessage:
    message: str


@dataclass
class SummaryFlightsOnly:
    number_of_flights: int
    timestamp: str


@dataclass
class FlightDetailsNotFoundMessage:
    message: str


@dataclass
class OperatorDetailsSuccessResponse:
    details: RIDFlightDetails

@dataclass
class OperationalIntentDetails:
    operational_intent: OperationalIntentDetailsUSSResponse


@dataclass
class UpdateChangedOpIntDetailsPost:
    operational_intent_id: str
    subscriptions: list[SubscriptionState]
    operational_intent: OperationalIntentDetailsUSSResponse | None = None


Latitude = float
"""Degrees of latitude north of the equator, with reference to the WGS84 ellipsoid."""


Longitude = float
"""Degrees of longitude east of the Prime Meridian, with reference to the WGS84 ellipsoid."""


class PositionAccuracyVertical(str, Enum):
    """Vertical error that is likely to be present in this reported position. This is the GVA enumeration from ADS-B, plus some finer values for UAS."""

    VAUnknown = "VAUnknown"
    VA150mPlus = "VA150mPlus"
    VA150m = "VA150m"
    VA45m = "VA45m"
    VA25m = "VA25m"
    VA10m = "VA10m"
    VA3m = "VA3m"
    VA1m = "VA1m"


class PositionAccuracyHorizontal(str, Enum):
    """Horizontal error that is likely to be present in this reported position. This is the NACp enumeration from ADS-B, plus 1m for a more complete range for UAS."""

    HAUnknown = "HAUnknown"
    HA10NMPlus = "HA10NMPlus"
    HA10NM = "HA10NM"
    HA4NM = "HA4NM"
    HA2NM = "HA2NM"
    HA1NM = "HA1NM"
    HA05NM = "HA05NM"
    HA03NM = "HA03NM"
    HA01NM = "HA01NM"
    HA005NM = "HA005NM"
    HA30m = "HA30m"
    HA10m = "HA10m"
    HA3m = "HA3m"
    HA1m = "HA1m"


@dataclass
class Position:
    """Location of the vehicle (UAS) as reported for UTM. Note: 'accuracy' values are required when extrapolated field is true."""

    longitude: Longitude | None
    latitude: Latitude | None
    accuracy_h: PositionAccuracyHorizontal | None
    accuracy_v: PositionAccuracyVertical | None
    altitude: Altitude | None
    extrapolated: bool | None = False


class VelocityUnitsSpeed(str, Enum):
    MetersPerSecond = "MetersPerSecond"


@dataclass
class Velocity:
    speed: float
    """Ground speed in meters/second."""
    units_speed: VelocityUnitsSpeed = VelocityUnitsSpeed.MetersPerSecond
    track: float | None = 0
    """Direction of flight expressed as a "True North-based" ground track angle. This value is provided in degrees East of North with a minimum resolution of 1 degree. A value of 360 indicates invalid, no value, or unknown."""


@dataclass
class VehicleTelemetry:
    """Vehicle position, altitude, and velocity."""

    time_measured: Time
    position: Position | None
    velocity: Velocity | None


@dataclass
class VehicleTelemetryResponse:
    operational_intent_id: str
    telemetry: VehicleTelemetry | None
    next_telemetry_opportunity: Time | None


class ExchangeRecordRecorderRole(str, Enum):
    """A coded value that indicates the role of the logging USS: 'Client' (initiating a request to a remote USS) or 'Server' (handling a request from a remote USS)"""

    Client = "Client"
    Server = "Server"


@dataclass
class ExchangeRecord:
    """Details of a request/response data exchange."""

    url: str
    """Full URL of request."""

    method: str
    """HTTP verb used by requester (e.g., "PUT," "GET," etc.)"""

    recorder_role: ExchangeRecordRecorderRole
    """A coded value that indicates the role of the logging USS: 'Client' (initiating a request to a remote USS) or 'Server' (handling a request from a remote USS)"""

    request_time: Time
    """The time at which the request was sent/received."""

    response_time: Time | None
    """The time at which the response was sent/received."""

    problem: str | None
    """'Human-readable description of the problem with the exchange, if any.'"""

    headers: list | None = field(default_factory=list)
    """Set of headers associated with request or response. Requires 'Authorization:' field (at a minimum)"""

    request_body: str | None = ""
    """Base64-encoded body content sent/received as a request."""

    response_body: str | None = ""
    """Base64-encoded body content sent/received in response to request."""

    response_code: int | None = 0
    """HTTP response code sent/received in response to request."""


@dataclass
class ErrorReport:
    """A report informing a server of a communication problem."""

    report_id: str | None
    """ID assigned by the server receiving the report.  Not populated when submitting a report."""

    exchange: ExchangeRecord
    """The request (by this USS) and response associated with the error."""
