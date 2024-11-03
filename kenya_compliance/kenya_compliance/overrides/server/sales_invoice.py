import frappe
from frappe.model.document import Document

from .shared_overrides import generic_invoices_on_submit_override


def on_submit(doc: Document, method: str) -> None:
    """Intercepts submit event for document"""

    if (
        doc.custom_successfully_submitted == 0
        and doc.update_stock == 1
        and doc.custom_defer_etims_submission == 0
    ):
        generic_invoices_on_submit_override(doc, "Sales Invoice")

def before_cancel(doc: Document, method: str) -> None:
    """Disallow cancelling of submitted invoice to eTIMS."""
    if doc.custom_successfully_submitted:
        frappe.throw(
            "This invoice has already been <b>submitted</b> to eTIMS and cannot be <span style='color:red'>canceled.</span>\n"
            "If you need to make adjustments, please create a Credit Note instead."
        )
