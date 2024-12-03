import frappe
import json
from ..utils import build_slade_headers, get_route_path, get_slade_server_url
from ..handlers import handle_slade_errors
from ..background_tasks.tasks import run_updater_functions, update_item_classification_codes, update_currencies
from .remote_response_status_handlers import notices_search_on_success, on_slade_error
from .api_builder import Slade360EndpointsBuilder
from ..doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    USER_DOCTYPE_NAME,
)

endpoints_builder = Slade360EndpointsBuilder()




def process_request(request_data: str, route_key: str, handler_function) -> None:
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
        
    return "Completed"


@frappe.whitelist()
def perform_notice_search(request_data: str) -> None:
    """Function to perform notice search."""
    return process_request(request_data, "NoticeSearchReq", notices_search_on_success)


@frappe.whitelist()
def refresh_code_lists(request_data: str) -> None:
    """Function to refresh code lists."""
    return process_request(request_data, "CodeSearchReq", run_updater_functions)


@frappe.whitelist()
def get_item_classification_codes(request_data: str) -> None:
    """Function to get item classification codes."""
    return process_request(request_data, "ItemClsSearchReq", update_item_classification_codes)


@frappe.whitelist()
def get_currencies(request_data: str) -> None:
    """Function to get currencies."""
    return process_request(request_data, "CurrencySearchReq", update_currencies)


