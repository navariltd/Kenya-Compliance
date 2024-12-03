import json

import frappe
import frappe.defaults
from frappe.model.document import Document

from ..apis.api_builder import EndpointsBuilder
from ..apis.remote_response_status_handlers import on_error
from ..doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
    PACKAGING_UNIT_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    TAXATION_TYPE_DOCTYPE_NAME,
    UNIT_OF_QUANTITY_DOCTYPE_NAME,
)
from ..overrides.server.stock_ledger_entry import on_update
from ..utils import (
    build_headers,
    get_route_path,
    get_server_url,
)

endpoints_builder = EndpointsBuilder()


def refresh_notices() -> None:
    from ..apis.apis import perform_notice_search

    company = frappe.defaults.get_user_default("Company")

    perform_notice_search(json.dumps({"company_name": company}))


def send_sales_invoices_information() -> None:
    from ..overrides.server.sales_invoice import on_submit

    all_submitted_unsent: list[Document] = frappe.get_all(
        "Sales Invoice", {"docstatus": 1, "custom_successfully_submitted": 0}, ["name"]
    )  # Fetch all Sales Invoice records according to filter

    if all_submitted_unsent:
        for sales_invoice in all_submitted_unsent:
            doc = frappe.get_doc(
                "Sales Invoice", sales_invoice.name, for_update=False
            )  # Refetch to get the document representation of the record

            try:
                on_submit(
                    doc, method=None
                )  # Delegate to the on_submit method for sales invoices

            except TypeError:
                continue


def send_pos_invoices_information() -> None:
    from ..overrides.server.sales_invoice import on_submit

    all_pending_pos_invoices: list[Document] = frappe.get_all(
        "POS Invoice", {"docstatus": 1, "custom_successfully_submitted": 0}, ["name"]
    )

    if all_pending_pos_invoices:
        for pos_invoice in all_pending_pos_invoices:
            doc = frappe.get_doc(
                "POS Invoice", pos_invoice.name, for_update=False
            )  # Refetch to get the document representation of the record

            try:
                on_submit(
                    doc, method=None
                )  # Delegate to the on_submit method for sales invoices

            except TypeError:
                continue


def send_stock_information() -> None:
    all_stock_ledger_entries: list[Document] = frappe.get_all(
        "Stock Ledger Entry",
        {"docstatus": 1, "custom_submitted_successfully": 0},
        ["name"],
    )
    for entry in all_stock_ledger_entries:
        doc = frappe.get_doc(
            "Stock Ledger Entry", entry.name, for_update=False
        )  # Refetch to get the document representation of the record

        try:
            on_update(
                doc, method=None
            )  # Delegate to the on_update method for Stock Ledger Entry override

        except TypeError:
            continue


def send_purchase_information() -> None:
    from ..overrides.server.purchase_invoice import on_submit

    all_submitted_purchase_invoices: list[Document] = frappe.get_all(
        "Purchase Invoice",
        {"docstatus": 1, "custom_submitted_successfully": 0},
        ["name"],
    )

    for invoice in all_submitted_purchase_invoices:
        doc = frappe.get_doc(
            "Purchase Invoice", invoice.name, for_update=False
        )  # Refetch to get the document representation of the record

        try:
            on_submit(doc, method=None)

        except TypeError:
            continue


def send_item_inventory_information() -> None:
    from ..apis.apis import submit_inventory

    query = """
        SELECT sle.name as name,
            sle.owner,
            sle.custom_submitted_successfully,
            sle.custom_inventory_submitted_successfully,
            qty_after_transaction as residual_qty,
            sle.warehouse,
            w.custom_branch as branch_id,
            i.item_code as item,
            custom_item_code_etims as item_code
        FROM `tabStock Ledger Entry` sle
            INNER JOIN tabItem i ON sle.item_code = i.item_code
            INNER JOIN tabWarehouse w ON sle.warehouse = w.name
        WHERE sle.custom_submitted_successfully = '1'
            AND sle.custom_inventory_submitted_successfully = '0'
        ORDER BY sle.creation DESC;
        """

    sles = frappe.db.sql(query, as_dict=True)

    for stock_ledger in sles:
        response = json.dumps(stock_ledger)

        try:
            submit_inventory(response)

        except Exception as error:
            # TODO: Suspicious looking type(error)
            frappe.throw("Error Encountered", type(error), title="Error")


@frappe.whitelist()
def refresh_code_lists(vendor: str = "OSCU KRA") -> str | None:
    company_name: str | None = frappe.defaults.get_user_default("Company")

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)

    code_search_route_path, last_request_date = get_route_path(
        "CodeSearchReq"
    )  # endpoint for code search

    if headers and server_url and code_search_route_path:
        url = f"{server_url}{code_search_route_path}"
        payload = {
            "lastReqDt": "20200101000000"
        }  # Hard-coded to this date to get all code lists.

        endpoints_builder.headers = headers
        endpoints_builder.payload = payload
        endpoints_builder.error_callback = on_error

        # Fetch and update codes obtained from CodeSearchReq endpoint
        endpoints_builder.url = url
        endpoints_builder.success_callback = run_updater_functions
        endpoints_builder.make_remote_call(doctype=None, document_name=None)

        return "succeeded"


@frappe.whitelist()
def get_item_classification_codes(vendor="OSCU KRA") -> str | None:
    company_name: str | None = frappe.defaults.get_user_default("Company")

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)

    item_cls_route_path, last_request_date = get_route_path(
        "ItemClsSearchReq"
    )  # overwriting last_request_date since it's not used elsewhere for this task

    if headers and server_url and item_cls_route_path:
        url = f"{server_url}{item_cls_route_path}"
        payload = {
            "lastReqDt": "20230101000000"
        }  # Hard-coded to a this date to get all code lists.

        endpoints_builder.url = url
        endpoints_builder.headers = headers
        endpoints_builder.payload = payload
        endpoints_builder.error_callback = on_error

        endpoints_builder.url = f"{server_url}{item_cls_route_path}"
        endpoints_builder.success_callback = update_item_classification_codes

        # endpoints_builder.make_remote_call(doctype=None, document_name=None)
        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="long",
            timeout=1200,
            doctype=SETTINGS_DOCTYPE_NAME,
        )

        return "succeeded"


def run_updater_functions(response: dict) -> None:
    for class_list in response["data"]["clsList"]:
        if class_list["cdClsNm"] == "Quantity Unit":
            update_unit_of_quantity(class_list)

        if class_list["cdClsNm"] == "Taxation Type":
            update_taxation_type(class_list)

        if class_list["cdClsNm"] == "Packing Unit":
            update_packaging_units(class_list)

        if class_list["cdClsNm"] == "Country":
            update_countries(class_list)


def update_documents(
    data: dict | list,
    doctype_name: str,
    field_mapping: dict,
    filter_field: str = "code",
) -> None:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON string: {data}")

    doc_list = data if isinstance(data, list) else data.get("results", data)

    for record in doc_list:
        if isinstance(record, str):
            continue

        filter_value = record.get(filter_field)
        try:
            doc = frappe.get_doc(doctype_name, filter_value)
        except frappe.DoesNotExistError:
            doc = frappe.new_doc(doctype_name)

        for field, value in field_mapping.items():
            if callable(value):
                setattr(doc, field, value(record))
            else:
                setattr(doc, field, record.get(value, ""))

        doc.save()

    frappe.db.commit()


def update_unit_of_quantity(data: dict) -> None:
    field_mapping = {
        "code": "code",
        "sort_order": "sort_order",
        "code_name": "name",
        "code_description": "description",
    }
    update_documents(data, UNIT_OF_QUANTITY_DOCTYPE_NAME, field_mapping)


def update_packaging_units(data: dict) -> None:
    field_mapping = {
        "code": "code",
        "code_name": "name",
        "sort_order": "sort_order",
        "code_description": "description",
    }
    update_documents(data, PACKAGING_UNIT_DOCTYPE_NAME, field_mapping)


def update_item_classification_codes(response: dict | list) -> None:
    field_mapping = {
        "itemclscd": "classification_code",
        "itemclslvl": "classification_level",
        "itemclsnm": "classification_name",
        "taxtycd": "tax_type_code",
        "useyn": lambda x: 1 if x.get("is_used") else 0,
        "mjrtgyn": lambda x: 1 if x.get("is_frequently_used") else 0,
    }
    update_documents(
        response,
        ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
        field_mapping,
        filter_field="classification_code",
    )


def update_taxation_type(data: dict) -> None:
    doc: Document | None = None
    tax_list = data.get("results", [])

    for taxation_type in tax_list:
        code = (
            taxation_type["tax_code"]
            if taxation_type["tax_code"]
            else taxation_type["name"]
        )
        try:
            doc = frappe.get_doc(TAXATION_TYPE_DOCTYPE_NAME, code)

        except:
            doc = frappe.new_doc(TAXATION_TYPE_DOCTYPE_NAME)

        finally:
            doc.cd = code
            doc.cdnm = taxation_type["name"]
            doc.cddesc = taxation_type["description"]
            doc.useyn = 1 if taxation_type["active"] else 0
            doc.srtord = taxation_type["percentage"]

            doc.save()

    frappe.db.commit()


def update_countries(data: list) -> None:
    doc: Document | None = None
    for code, details in data.items():
        try:
            country_name = details.get("name", "").strip().lower()
            doc = frappe.get_doc(
                COUNTRIES_DOCTYPE_NAME, {"name": ["like", country_name]}
            )
        except:
            doc = frappe.new_doc(COUNTRIES_DOCTYPE_NAME)

        doc.code = code
        doc.code_name = details.get("name")
        doc.currency_code = details.get("currency_code")
        doc.sort_order = details.get("sort_order", 0)
        doc.code_description = details.get("description", "")

        doc.save()

    frappe.db.commit()
