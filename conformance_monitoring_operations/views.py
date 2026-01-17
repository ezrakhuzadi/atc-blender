# Create your views here.
# Create your views here.

from dataclasses import asdict

import arrow
from django.http import JsonResponse
from rest_framework.decorators import api_view

from auth_helper.utils import requires_scopes
from common.data_definitions import FLIGHTBLENDER_READ_SCOPE
from common.database_operations import FlightBlenderDatabaseReader
from flight_declaration_operations.models import FlightDeclaration

from .conformance_state_helper import ConformanceChecksList
from .data_definitions import ConformanceSummary
from .models import ConformanceRecord


DEFAULT_LOOKBACK_HOURS = 24


def _serialize_record(record: ConformanceRecord) -> dict:
    return {
        "id": str(record.id),
        "flight_declaration_id": str(record.flight_declaration_id),
        "aircraft_id": record.flight_declaration.aircraft_id,
        "conformance_state": record.conformance_state,
        "conformance_state_label": record.get_conformance_state_display_text(),
        "conformance_state_code": (
            ConformanceChecksList.state_code(record.conformance_state)
            if record.conformance_state in ConformanceChecksList.keys()
            else None
        ),
        "timestamp": record.timestamp.isoformat(),
        "description": record.description,
        "event_type": record.event_type,
        "geofence_breach": record.geofence_breach,
        "geofence_id": str(record.geofence_id) if record.geofence_id else None,
        "resolved": record.resolved,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _derive_status(record: ConformanceRecord | None) -> str:
    if record is None:
        return "unknown"
    if record.resolved:
        return "conforming"
    if record.event_type == "rectification":
        return "conforming"
    if record.conformance_state == 1:
        return "conforming"
    return "nonconforming"


def _parse_date_range(params):
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    if start_date and end_date:
        try:
            start_datetime = arrow.get(start_date)
            end_datetime = arrow.get(end_date)
        except arrow.ParserError:
            return None, None, JsonResponse({"error": "Invalid date format. Use ISO 8601 format."}, status=400)
        if start_datetime >= end_datetime:
            return None, None, JsonResponse({"error": "start_date must be before end_date"}, status=400)
        return start_datetime, end_datetime, None

    if start_date or end_date:
        return None, None, JsonResponse({"error": "start_date and end_date must be provided together"}, status=400)

    end_datetime = arrow.utcnow()
    start_datetime = end_datetime.shift(hours=-DEFAULT_LOOKBACK_HOURS)
    return start_datetime, end_datetime, None


def _filter_records(records, params):
    flight_declaration_id = params.get("flight_declaration_id")
    aircraft_id = params.get("aircraft_id")
    if flight_declaration_id:
        records = records.filter(flight_declaration__id=flight_declaration_id)
    if aircraft_id:
        records = records.filter(flight_declaration__aircraft_id=aircraft_id)
    return records


@api_view(["GET"])
@requires_scopes([FLIGHTBLENDER_READ_SCOPE])
def conformance_status(request):
    params = request.query_params
    flight_declaration_id = params.get("flight_declaration_id")
    aircraft_id = params.get("aircraft_id")

    if not flight_declaration_id and not aircraft_id:
        return JsonResponse({"error": "aircraft_id or flight_declaration_id is required"}, status=400)

    if flight_declaration_id:
        flight_declarations = FlightDeclaration.objects.filter(id=flight_declaration_id)
    else:
        flight_declarations = FlightDeclaration.objects.filter(aircraft_id=aircraft_id)

    if not flight_declarations.exists():
        return JsonResponse(
            {"status": "unknown", "record": None},
            status=200,
        )

    latest_record = (
        ConformanceRecord.objects.filter(flight_declaration__in=flight_declarations)
        .order_by("-created_at")
        .first()
    )

    return JsonResponse(
        {
            "status": _derive_status(latest_record),
            "record": _serialize_record(latest_record) if latest_record else None,
        }
    )


@api_view(["GET"])
@requires_scopes([FLIGHTBLENDER_READ_SCOPE])
def get_conformance_records(request):
    # Implement logic to retrieve and return conformance record summary
    my_database_reader = FlightBlenderDatabaseReader()
    start_datetime, end_datetime, error_response = _parse_date_range(request.query_params)
    if error_response:
        return error_response

    all_conformance_records = my_database_reader.get_conformance_records_for_duration(
        start_time=start_datetime, end_time=end_datetime
    )
    if all_conformance_records is None:
        return JsonResponse({"conformance_records": []})

    filtered_records = _filter_records(all_conformance_records, request.query_params)
    limit = request.query_params.get("limit")
    if limit:
        try:
            limit_value = int(limit)
            if limit_value > 0:
                filtered_records = filtered_records[:limit_value]
        except ValueError:
            return JsonResponse({"error": "limit must be an integer"}, status=400)

    return JsonResponse(
        {
            "conformance_records": [
                _serialize_record(record) for record in filtered_records
            ]
        }
    )


@api_view(["GET"])
@requires_scopes([FLIGHTBLENDER_READ_SCOPE])
def get_conformance_record_summary(request):
    # Implement logic to retrieve and return conformance record summary
    my_database_reader = FlightBlenderDatabaseReader()
    start_datetime, end_datetime, error_response = _parse_date_range(request.query_params)
    if error_response:
        return error_response

    all_conformance_records = my_database_reader.get_conformance_records_for_duration(
        start_time=start_datetime, end_time=end_datetime
    )
    if all_conformance_records is None:
        all_conformance_records = []

    filtered_records = _filter_records(all_conformance_records, request.query_params)
    # Calculate summary statistics
    total_records = len(filtered_records)
    conforming_records = sum(1 for record in filtered_records if _derive_status(record) == "conforming")
    non_conforming_records = total_records - conforming_records
    conformance_rate = (conforming_records / total_records * 100) if total_records > 0 else 0

    summary = asdict(
        ConformanceSummary(
            total_records=total_records,
            conforming_records=conforming_records,
            non_conforming_records=non_conforming_records,
            conformance_rate_percentage=conformance_rate,
            start_date=start_datetime.isoformat(),
            end_date=end_datetime.isoformat(),
        )
    )

    return JsonResponse({"summary": summary})
