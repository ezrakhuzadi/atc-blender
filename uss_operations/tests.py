import base64
import json
import os
import uuid

from django.test import TestCase

from flight_declaration_operations.models import FlightDeclaration
from flight_feed_operations.models import FlightObservation


def _b64url(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def make_dummy_jwt(scopes: list[str]) -> str:
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"scope": " ".join(scopes), "iss": "dummy", "aud": "test"}
    signature = base64.urlsafe_b64encode(b"signature").decode("utf-8").rstrip("=")
    return f"{_b64url(header)}.{_b64url(payload)}.{signature}"


class USSOffNominalPositionDetailsTests(TestCase):
    def setUp(self) -> None:
        os.environ["BYPASS_AUTH_TOKEN_VERIFICATION"] = "1"
        os.environ["IS_DEBUG"] = "1"

    def test_returns_404_when_unknown(self):
        token = make_dummy_jwt(["utm.strategic_coordination"])
        unknown_id = uuid.uuid4()
        resp = self.client.get(
            f"/uss/v1/operational_intents/{unknown_id}/off_nominal_position",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 404)

    def test_returns_telemetry_when_observation_exists(self):
        token = make_dummy_jwt(["utm.strategic_coordination"])

        flight_declaration = FlightDeclaration.objects.create(
            operational_intent="{}",
            bounds="0,0,0,0",
            aircraft_id="TEST-AIRCRAFT",
        )
        FlightObservation.objects.create(
            session_id=flight_declaration.id,
            latitude_dd=33.0,
            longitude_dd=-117.0,
            altitude_mm=1234.0,
            traffic_source=9,
            source_type=0,
            icao_address="ABC123",
            metadata="{}",
        )

        resp = self.client.get(
            f"/uss/v1/operational_intents/{flight_declaration.id}/off_nominal_position",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["operational_intent_id"], str(flight_declaration.id))
        self.assertIsNotNone(data["telemetry"])
        self.assertIsNotNone(data["telemetry"]["position"])
        self.assertEqual(data["telemetry"]["position"]["latitude"], 33.0)
        self.assertEqual(data["telemetry"]["position"]["longitude"], -117.0)
        self.assertAlmostEqual(data["telemetry"]["position"]["altitude"]["value"], 1.234, places=3)


class USSOpIntDetailTelemetryTests(TestCase):
    def setUp(self) -> None:
        os.environ["BYPASS_AUTH_TOKEN_VERIFICATION"] = "1"
        os.environ["IS_DEBUG"] = "1"

    def test_returns_404_when_unknown(self):
        token = make_dummy_jwt(["utm.conformance_monitoring_sa"])
        unknown_id = uuid.uuid4()
        resp = self.client.get(
            f"/uss/v1/operational_intents/{unknown_id}/telemetry",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 404)

    def test_returns_telemetry_when_observation_exists(self):
        token = make_dummy_jwt(["utm.conformance_monitoring_sa"])

        flight_declaration = FlightDeclaration.objects.create(
            operational_intent="{}",
            bounds="0,0,0,0",
            aircraft_id="TEST-AIRCRAFT",
        )
        FlightObservation.objects.create(
            session_id=flight_declaration.id,
            latitude_dd=33.1,
            longitude_dd=-117.1,
            altitude_mm=4321.0,
            traffic_source=9,
            source_type=0,
            icao_address="DEF456",
            metadata="{}",
        )

        resp = self.client.get(
            f"/uss/v1/operational_intents/{flight_declaration.id}/telemetry",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["operational_intent_id"], str(flight_declaration.id))
        self.assertIsNotNone(data["telemetry"])
        self.assertIsNotNone(data["telemetry"]["position"])
        self.assertEqual(data["telemetry"]["position"]["latitude"], 33.1)
        self.assertEqual(data["telemetry"]["position"]["longitude"], -117.1)
        self.assertAlmostEqual(data["telemetry"]["position"]["altitude"]["value"], 4.321, places=3)
