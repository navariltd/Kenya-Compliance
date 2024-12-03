import json

import frappe
from frappe.model.document import Document

from .logger import etims_logger
from .utils import update_last_request_date


def handle_errors(
    response: dict[str, str],
    route: str,
    document_name: str,
    doctype: str | Document | None = None,
    integration_request_name: str | None = None,
) -> None:
    error_message, error_code = response["resultMsg"], response["resultCd"]

    etims_logger.error("%s, Code: %s" % (error_message, error_code))

    try:
        frappe.throw(
            error_message,
            frappe.InvalidStatusError,
            title=f"Error: {error_code}",
        )

    except frappe.InvalidStatusError as error:
        frappe.log_error(
            frappe.get_traceback(with_context=True),
            error,
            reference_name=document_name,
            reference_doctype=doctype,
        )
        raise

    finally:
        update_last_request_date(response["resultDt"], route)


def handle_slade_errors(
    response: dict[str, str],
    route: str,
    document_name: str | None = None,
    doctype: str | Document | None = None,
    integration_request_name: str | None = None,
) -> None:
    # Prepare detailed error message
    error_detail = json.dumps(
        response, indent=4
    )  # Format error details for readability
    log_message = f"Error in route: {route}\n"
    log_message += f"Response: {error_detail}\n"

    # Add optional context to the log message if available
    if document_name:
        log_message += f"Document Name: {document_name}\n"
    if doctype:
        log_message += f"Doctype: {doctype}\n"
    if integration_request_name:
        log_message += f"Integration Request Name: {integration_request_name}\n"

    try:
        # Log the error with more context in the error message
        frappe.log_error(message=log_message, title="Slade Error")
    except Exception as e:
        # If logging fails, fall back to standard error logging
        etims_logger.error(f"Error while logging Slade error: {str(e)}")
