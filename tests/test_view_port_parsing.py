import unittest

from rid_operations import view_port_ops


class TestViewPortParsing(unittest.TestCase):
    def test_parse_view_lat_lng_accepts_valid(self):
        view = "33.0,-117.0,34.0,-116.0"
        coords = view_port_ops.parse_view_lat_lng(view)
        self.assertEqual(coords, [33.0, -117.0, 34.0, -116.0])

    def test_parse_view_lat_lng_rejects_wrong_count(self):
        with self.assertRaises(view_port_ops.ViewPortParseError):
            view_port_ops.parse_view_lat_lng("1,2,3")

    def test_parse_view_lat_lng_rejects_non_numeric(self):
        with self.assertRaises(view_port_ops.ViewPortParseError):
            view_port_ops.parse_view_lat_lng("a,b,c,d")

    def test_parse_view_lat_lng_rejects_out_of_bounds(self):
        with self.assertRaises(view_port_ops.ViewPortParseError):
            view_port_ops.parse_view_lat_lng("91,0,92,1")

    def test_parse_view_lat_lng_rejects_too_long(self):
        with self.assertRaises(view_port_ops.ViewPortParseError):
            view_port_ops.parse_view_lat_lng("1," * 500, max_length=10)

    def test_parse_view_minx_miny_accepts_valid(self):
        view = "-117.0,33.0,-116.0,34.0"
        coords = view_port_ops.parse_view_minx_miny(view)
        self.assertEqual(coords, [-117.0, 33.0, -116.0, 34.0])

    def test_parse_view_minx_miny_accepts_whitespace(self):
        view = " -117.0 , 33.0 , -116.0 , 34.0 "
        coords = view_port_ops.parse_view_minx_miny(view)
        self.assertEqual(coords, [-117.0, 33.0, -116.0, 34.0])

    def test_parse_view_minx_miny_rejects_out_of_bounds(self):
        with self.assertRaises(view_port_ops.ViewPortParseError):
            view_port_ops.parse_view_minx_miny("-200,0,0,1")

