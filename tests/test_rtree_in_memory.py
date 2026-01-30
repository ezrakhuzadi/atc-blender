import unittest

from flight_declaration_operations.flight_declarations_rtree_helper import FlightDeclarationRTreeIndexFactory
from geo_fence_operations.rtree_geo_fence_helper import GeoFenceRTreeIndexFactory


class _DummyBoundsObject:
    def __init__(self, object_id: int, bounds: str):
        self.id = object_id
        self.bounds = bounds


class TestRTreeInMemory(unittest.TestCase):
    def test_geofence_index_clears_without_leaving_stale_entries(self):
        factory = GeoFenceRTreeIndexFactory()
        fences = [
            _DummyBoundsObject(1, "-117.9,33.6,-117.8,33.7"),
            _DummyBoundsObject(2, "-118.0,33.5,-117.95,33.55"),
        ]
        factory.generate_geo_fence_index(all_fences=fences)

        hits = factory.check_box_intersection(view_box=[33.0, -118.5, 34.0, -117.0])
        self.assertEqual(len(hits), 2)

        factory.clear_rtree_index()
        hits_after_clear = factory.check_box_intersection(view_box=[33.0, -118.5, 34.0, -117.0])
        self.assertEqual(hits_after_clear, [])

    def test_flight_declaration_index_clears_without_leaving_stale_entries(self):
        factory = FlightDeclarationRTreeIndexFactory()
        declarations = [
            _DummyBoundsObject(1, "-117.9,33.6,-117.8,33.7"),
        ]
        factory.generate_flight_declaration_index(all_flight_declarations=declarations)

        hits = factory.check_flight_declaration_box_intersection(view_box=[-118.0, 33.0, -117.0, 34.0])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].flight_declaration_id, "1")

        factory.clear_rtree_index()
        hits_after_clear = factory.check_flight_declaration_box_intersection(view_box=[-118.0, 33.0, -117.0, 34.0])
        self.assertEqual(hits_after_clear, [])
