import unittest
from unittest.mock import patch

import arrow

from surveillance_monitoring_operations.data_definitions import ActiveTrack
from surveillance_monitoring_operations.utils import TrafficDataFuser


class TestSurveillanceTrackGeneration(unittest.TestCase):
    def test_lon_not_flipped_and_alt_converted_to_meters(self):
        session_id = "00000000-0000-0000-0000-000000000000"
        aircraft_id = "aircraft-1"

        track = ActiveTrack(
            session_id=session_id,
            unique_aircraft_identifier=aircraft_id,
            last_updated_timestamp=arrow.utcnow().isoformat(),
            observations=[
                {
                    "session_id": session_id,
                    "lat_dd": 33.6846,
                    "lon_dd": -117.8265,
                    "altitude_mm": 1000.0,
                    "timestamp": 1000,
                    "traffic_source": 1,
                    "source_type": 1,
                    "icao_address": aircraft_id,
                    "metadata": {},
                },
                {
                    "session_id": session_id,
                    "lat_dd": 33.6847,
                    "lon_dd": -117.8266,
                    "altitude_mm": 2000.0,
                    "timestamp": 1001,
                    "traffic_source": 1,
                    "source_type": 1,
                    "icao_address": aircraft_id,
                    "metadata": {},
                },
            ],
        )

        with patch("surveillance_monitoring_operations.utils.RedisStreamOperations"):
            fuser = TrafficDataFuser(session_id=session_id, raw_observations=[])
            messages = fuser.generate_track_messages(active_tracks=[track])

        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertAlmostEqual(message.state.position.lng, -117.8266, places=6)
        self.assertAlmostEqual(message.state.position.alt, 2.0, places=6)
        self.assertAlmostEqual(message.state.position.pressure_altitude, 2.0, places=6)

    def test_duplicate_timestamps_do_not_crash(self):
        session_id = "00000000-0000-0000-0000-000000000000"
        aircraft_id = "aircraft-1"

        track = ActiveTrack(
            session_id=session_id,
            unique_aircraft_identifier=aircraft_id,
            last_updated_timestamp=arrow.utcnow().isoformat(),
            observations=[
                {
                    "session_id": session_id,
                    "lat_dd": 33.6846,
                    "lon_dd": -117.8265,
                    "altitude_mm": 1000.0,
                    "timestamp": 1000,
                    "traffic_source": 1,
                    "source_type": 1,
                    "icao_address": aircraft_id,
                    "metadata": {},
                },
                {
                    "session_id": session_id,
                    "lat_dd": 33.6847,
                    "lon_dd": -117.8266,
                    "altitude_mm": 2000.0,
                    "timestamp": 1000,
                    "traffic_source": 1,
                    "source_type": 1,
                    "icao_address": aircraft_id,
                    "metadata": {},
                },
            ],
        )

        with patch("surveillance_monitoring_operations.utils.RedisStreamOperations"):
            fuser = TrafficDataFuser(session_id=session_id, raw_observations=[])
            messages = fuser.generate_track_messages(active_tracks=[track])

        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message.state.speed, 0.0)
