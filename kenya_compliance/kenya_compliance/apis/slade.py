import json

import frappe

from ..background_tasks.tasks import (
    update_countries,
    update_item_classification_codes,
    update_packaging_units,
    update_taxation_type,
    update_unit_of_quantity,
)
from ..doctype.doctype_names_mapping import SETTINGS_DOCTYPE_NAME
from ..utils import build_slade_headers, get_route_path, get_slade_server_url
from .api_builder import Slade360EndpointsBuilder
from .remote_response_status_handlers import notices_search_on_success, on_slade_error

endpoints_builder = Slade360EndpointsBuilder()


def process_request(request_data: str, route_key: str, handler_function) -> str:
    """Reusable function to process requests with common logic."""
    data = json.loads(request_data)
    company_name = data.get("company_name")

    headers = build_slade_headers(company_name)
    server_url = get_slade_server_url(company_name)
    route_path, _ = get_route_path(route_key, "VSCU Slade 360")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.method = "GET"
        endpoints_builder.success_callback = handler_function
        endpoints_builder.error_callback = on_slade_error

        endpoints_builder.make_remote_call(
            doctype=SETTINGS_DOCTYPE_NAME,
            document_name=data.get("name", None),
        )

        return f"{route_key} completed successfully."
    else:
        return f"Failed to process {route_key}. Missing required configuration."


@frappe.whitelist()
def perform_notice_search(request_data: str) -> str:
    """Function to perform notice search."""
    message = process_request(
        request_data, "NoticeSearchReq", notices_search_on_success
    )
    return message


@frappe.whitelist()
def refresh_code_lists(request_data: str) -> str:
    """Refresh code lists based on request data."""
    tasks = [
        ("CurrencySearchReq", update_countries),
        ("PackagingUnitSearchReq", update_packaging_units),
        ("UOMSearchReq", update_unit_of_quantity),
        ("TaxSearchReq", update_taxation_type),
    ]

    messages = [process_request(request_data, task[0], task[1]) for task in tasks]

    return " ".join(messages)


@frappe.whitelist()
def get_item_classification_codes(request_data: str) -> str:
    """Function to get item classification codes."""
    message = process_request(
        request_data, "ItemClsSearchReq", update_item_classification_codes
    )
    return message
