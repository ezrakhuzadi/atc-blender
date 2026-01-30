import arrow
from rtree import index
from shapely.geometry import Polygon

from common.database_operations import FlightBlenderDatabaseReader
from scd_operations.scd_data_definitions import Altitude, OpInttoCheckDetails, Time


class OperationalIntentComparisonFactory:
    """A method to check if two operational intents are same in geometry / time and altitude."""

    def check_volume_geometry_same(self, polygon_a: Polygon, polygon_b: Polygon) -> bool:
        return polygon_a.equals(polygon_b)  # Also has exact_equals and almost_equals method

    def check_volume_start_end_time_same(self, time_a: Time, time_b: Time) -> bool:
        try:
            return arrow.get(time_a.value) == arrow.get(time_b.value)
        except Exception:
            return False

    def check_volume_(self, altitude_a: Altitude, altitude_b: Altitude) -> bool:
        if altitude_a.reference != altitude_b.reference:
            return False

        value_a = self._to_meters(altitude_a)
        value_b = self._to_meters(altitude_b)
        if value_a is None or value_b is None:
            return False
        return abs(value_a - value_b) < 1e-6

    def _to_meters(self, altitude: Altitude) -> float | None:
        units = altitude.units.upper()
        if units in ["M", "METER", "METERS"]:
            return float(altitude.value)
        if units in ["FT", "FEET"]:
            return float(altitude.value) * 0.3048
        return None


class OperationalIntentsIndexFactory:
    def __init__(self):
        # Use an in-memory index to avoid cross-worker contamination and stale on-disk state.
        self.idx = index.Index()

    def add_box_to_index(
        self,
        enumerated_id: int,
        flight_id: str,
        view: list[float],
        start_time: str,
        end_time: str,
    ):
        metadata = {
            "start_time": start_time,
            "end_time": end_time,
            "flight_id": flight_id,
        }
        self.idx.insert(
            id=enumerated_id,
            coordinates=(view[0], view[1], view[2], view[3]),
            obj=metadata,
        )

    def delete_from_index(self, enumerated_id: int, view: list[float]):
        self.idx.delete(id=enumerated_id, coordinates=(view[0], view[1], view[2], view[3]))

    def check_op_ints_exist(self) -> bool:
        """This method generates a rTree index of currently active operational indexes"""
        my_database_reader = FlightBlenderDatabaseReader()
        return my_database_reader.check_active_activated_flights_exist()

    def generate_active_flights_operational_intents_index(self) -> None:
        """This method generates a rTree index of currently active operational intents"""

        my_database_reader = FlightBlenderDatabaseReader()
        flight_declarations = my_database_reader.get_active_activated_flight_declarations()

        for enumerated_id, flight_declaration in enumerate(flight_declarations):
            flight_id_str = str(flight_declaration.id)

            split_view = flight_declaration.bounds.split(",")
            start_time = flight_declaration.start_datetime
            end_time = flight_declaration.end_datetime
            view = [float(i) for i in split_view]

            self.add_box_to_index(
                enumerated_id=enumerated_id,
                flight_id=flight_id_str,
                view=view,
                start_time=start_time,
                end_time=end_time,
            )

    def clear_rtree_index(self):
        """Clear the in-memory RTree index."""
        try:
            self.idx.close()
        except Exception:
            pass
        self.idx = index.Index()

    def close_index(self):
        """Method to delete / close index"""
        self.idx.close()

    def check_box_intersection(self, view_box: list[float]):
        intersections = [n.object for n in self.idx.intersection((view_box[0], view_box[1], view_box[2], view_box[3]), objects=True)]
        return intersections


def check_polygon_intersection(op_int_details: list[OpInttoCheckDetails], polygon_to_check: Polygon) -> bool:
    idx = index.Index()

    for pos, op_int_detail in enumerate(op_int_details):
        idx.insert(pos, op_int_detail.shape.bounds)

    op_ints_of_interest_ids = list(idx.intersection(polygon_to_check.bounds))
    does_intersect = []
    if op_ints_of_interest_ids:
        for op_ints_of_interest_id in op_ints_of_interest_ids:
            existing_op_int = op_int_details[op_ints_of_interest_id]
            intersects = polygon_to_check.intersects(existing_op_int.shape)
            if intersects:
                does_intersect.append(True)
            else:
                does_intersect.append(False)

        return all(does_intersect)
    else:
        return False


def check_time_intersection(op_int_details: list[OpInttoCheckDetails], volume_time_end: str, volume_time_start: str) -> bool:
    """Method to check if a polygon is conflicted in time with existing operational intents"""
    _volume_time_start = arrow.get(volume_time_start)
    _volume_time_end = arrow.get(volume_time_end)
    does_time_intersect = []
    for existing_op_int in op_int_details:
        if not (_volume_time_end < arrow.get(existing_op_int.time_start) or _volume_time_start > arrow.get(existing_op_int.time_end)):
            does_time_intersect.append(True)
        else:
            does_time_intersect.append(False)

    return any(does_time_intersect)
