from django.urls import path

from . import views as conformance_views

urlpatterns = [
    path("conformance_status/", conformance_views.conformance_status, name="conformance_status"),
    path("get_conformance_records/", conformance_views.get_conformance_records, name="get_conformance_records"),
    path(
        "get_conformance_record_summary/",
        conformance_views.get_conformance_record_summary,
        name="get_conformance_record_summary",
    ),
]
