from dataclasses import asdict
from typing import Any
from collections.abc import Iterable

import arrow
from rtree import index

from .data_definitions import FlightDeclarationMetadata


class FlightDeclarationRTreeIndexFactory:
    """
    A factory class for managing an RTree index of flight declarations.
    Methods:
        __init__(index_name: str):
            Initializes the RTree index with the given name.
        add_box_to_index(id: int, flight_declaration_id: str, view: List[float], start_date: str, end_date: str) -> None:
        delete_from_index(enumerated_id: int, view: List[float]) -> None:
        generate_flight_declaration_index(all_flight_declarations: Union[QuerySet, List[FlightDeclaration]]) -> None:
        clear_rtree_index() -> None:
        check_flight_declaration_box_intersection(view_box: List[float]) -> List[FlightDeclarationMetadata]:
    """

    def __init__(self):
        # Use an in-memory index to avoid cross-worker contamination and stale on-disk state.
        self.idx = index.Index()

    def add_box_to_index(
        self,
        id: int,
        flight_declaration_id: str,
        view: list[float],
        start_date: str,
        end_date: str,
    ) -> None:
        """
        Adds a bounding box to the RTree index.

        Args:
            id (int): The unique identifier for the box.
            flight_declaration_id (str): The flight declaration ID.
            view (List[float]): The bounding box coordinates [minx, miny, maxx, maxy].
            start_date (str): The start date of the flight declaration.
            end_date (str): The end date of the flight declaration.
        """
        metadata = FlightDeclarationMetadata(start_date=start_date, end_date=end_date, flight_declaration_id=flight_declaration_id)
        self.idx.insert(id=id, coordinates=(view[0], view[1], view[2], view[3]), obj=asdict(metadata))

    def delete_from_index(self, enumerated_id: int, view: list[float]) -> None:
        """
        Deletes a bounding box from the RTree index.

        Args:
            enumerated_id (int): The unique identifier for the box.
            view (List[float]): The bounding box coordinates [minx, miny, maxx, maxy].
        """
        self.idx.delete(id=enumerated_id, coordinates=(view[0], view[1], view[2], view[3]))

    def generate_flight_declaration_index(self, all_flight_declarations: Iterable[Any]) -> None:
        """
        Generates an RTree index of currently active operational indexes.

        Args:
            all_flight_declarations: An iterable of objects with `id` and `bounds` attributes to be indexed.
        """
        present = arrow.now()
        start_date = present.shift(days=-1).isoformat()
        end_date = present.shift(days=1).isoformat()
        for enumerated_id, flight_declaration in enumerate(all_flight_declarations):
            declaration_idx_str = str(flight_declaration.id)
            view = [float(i) for i in flight_declaration.bounds.split(",")]
            self.add_box_to_index(
                id=enumerated_id,
                flight_declaration_id=declaration_idx_str,
                view=view,
                start_date=start_date,
                end_date=end_date,
            )

    def clear_rtree_index(self) -> None:
        """Clear the in-memory RTree index."""
        try:
            self.idx.close()
        except Exception:
            pass
        self.idx = index.Index()

    def check_flight_declaration_box_intersection(self, view_box: list[float]) -> list[FlightDeclarationMetadata]:
        """
        Checks for intersections with a given bounding box.

        Args:
            view_box (List[float]): The bounding box coordinates [minx, miny, maxx, maxy].

        Returns:
            List[FlightDeclarationMetadata]: A list of metadata for intersecting boxes.
        """
        intersections = [
            FlightDeclarationMetadata(**n.object) for n in self.idx.intersection((view_box[0], view_box[1], view_box[2], view_box[3]), objects=True)
        ]

        return intersections
