import json
from dataclasses import asdict
from os import environ as env
from urllib.parse import urljoin

import arrow
import requests
from loguru import logger
from requests.exceptions import ConnectionError
from shapely.geometry import shape
from shapely.ops import unary_union

from auth_helper.common import get_redis
from flight_blender.celery import app

from .common import GeoZoneParser
from .data_definitions import GeoAwarenessTestStatus, GeoZone
from .models import GeoFence
from .url_safety import validate_public_url

REQUEST_TIMEOUT_S = float(env.get("HTTP_TIMEOUT_S", "10"))
GEOZONE_MAX_DOWNLOAD_BYTES = int(env.get("GEOZONE_MAX_DOWNLOAD_BYTES", "5000000"))
GEOZONE_MAX_REDIRECTS = int(env.get("GEOZONE_MAX_REDIRECTS", "3"))


class GeoZoneDownloadError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _fetch_geozone_json(url: str) -> dict:
    allow_http = bool(int(env.get("IS_DEBUG", "0")))
    current_url = url

    for hop in range(GEOZONE_MAX_REDIRECTS + 1):
        ok, reason = validate_public_url(current_url, allow_http=allow_http, require_https=True)
        if not ok:
            raise GeoZoneDownloadError(f"url_not_allowed:{reason}")

        headers = {"Accept": "application/json"}
        try:
            with requests.get(
                current_url,
                timeout=REQUEST_TIMEOUT_S,
                allow_redirects=False,
                stream=True,
                headers=headers,
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise GeoZoneDownloadError("redirect_without_location")
                    current_url = urljoin(current_url, location)
                    continue

                if response.status_code != 200:
                    raise GeoZoneDownloadError(f"http_status:{response.status_code}")

                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > GEOZONE_MAX_DOWNLOAD_BYTES:
                            raise GeoZoneDownloadError("response_too_large")
                    except ValueError:
                        pass

                content_type = (response.headers.get("Content-Type") or "").lower()
                if content_type and "json" not in content_type:
                    raise GeoZoneDownloadError("unsupported_content_type")

                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > GEOZONE_MAX_DOWNLOAD_BYTES:
                        raise GeoZoneDownloadError("response_too_large")
                    chunks.append(chunk)

                raw = b"".join(chunks)
        except requests.exceptions.RequestException as error:
            raise GeoZoneDownloadError(f"request_failed:{error}") from error

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GeoZoneDownloadError("invalid_json") from error

        if not isinstance(data, dict):
            raise GeoZoneDownloadError("json_not_object")
        return data

    raise GeoZoneDownloadError("too_many_redirects")


@app.task(name="download_geozone_source")
def download_geozone_source(geo_zone_url: str, geozone_source_id: str):
    r = get_redis()
    geoawareness_test_data_store = "geoawarenes_test." + str(geozone_source_id)
    try:
        geo_zone_data = _fetch_geozone_json(geo_zone_url)
    except ConnectionError as ce:
        logger.error("Error in downloading data from Geofence url")
        logger.error(ce)
        test_status_storage = GeoAwarenessTestStatus(result="Error", message="Error in downloading data")
    except GeoZoneDownloadError as error:
        logger.error(f"GeoZone download rejected/failed: {error.message}")
        result = "Rejected" if error.message.startswith("url_not_allowed:") else "Error"
        test_status_storage = GeoAwarenessTestStatus(result=result, message=error.message)
    else:
        try:
            geo_zone_str = json.dumps(geo_zone_data)
            write_geo_zone.delay(geo_zone=geo_zone_str, test_harness_datasource="1")
            test_status_storage = GeoAwarenessTestStatus(result="Ready", message="")
        except Exception as error:  # noqa: BLE001
            logger.error(f"GeoZone processing failed: {error}")
            test_status_storage = GeoAwarenessTestStatus(result="Error", message="Failed to queue GeoZone processing")

    if r.exists(geoawareness_test_data_store):
        r.set(geoawareness_test_data_store, json.dumps(asdict(test_status_storage)))


@app.task(name="write_geo_zone")
def write_geo_zone(geo_zone: str, test_harness_datasource: str = "0"):
    geo_zone = json.loads(geo_zone)
    test_harness_datasource = int(test_harness_datasource)
    my_geo_zone_parser = GeoZoneParser(geo_zone=geo_zone)

    parse_response = my_geo_zone_parser.parse_validate_geozone()

    # all_zones_valid = parse_response.all_zones
    processed_geo_zone_features = parse_response.feature_list

    logger.info("Processing %s geozone features.." % len(processed_geo_zone_features))
    for geo_zone_feature in processed_geo_zone_features:
        all_feat_geoms = geo_zone_feature.geometry

        fc = {"type": "FeatureCollection", "features": []}
        all_shapes = []
        for g in all_feat_geoms:
            f = {"type": "Feature", "properties": {}, "geometry": {}}
            s = shape(g["horizontalProjection"])
            f["geometry"] = g["horizontalProjection"]
            fc["features"].append(f)
            all_shapes.append(s)
        u = unary_union(all_shapes)
        bounds = u.bounds
        bounds_str = ",".join([str(x) for x in bounds])

        logger.debug(f"Bounding box for shape.. {bounds}")

        geo_zone = GeoZone(
            title=geo_zone["title"],
            description=geo_zone["description"],
            features=geo_zone_feature,
        )
        name = geo_zone_feature.name
        start_time = arrow.now()
        end_time = start_time.shift(years=1)
        upper_limit = geo_zone_feature["upperLimit"] if "upperLimit" in geo_zone_feature else 300
        lower_limit = geo_zone_feature["lowerLimit"] if "lowerLimit" in geo_zone_feature else 10
        geo_f = GeoFence(
            geozone=json.dumps(geo_zone_feature),
            raw_geo_fence=json.dumps(fc),
            start_datetime=start_time.isoformat(),
            end_datetime=end_time.isoformat(),
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            bounds=bounds_str,
            name=name,
            is_test_dataset=test_harness_datasource,
        )
        geo_f.save()

        logger.info("Saved Geofence to database ..")
