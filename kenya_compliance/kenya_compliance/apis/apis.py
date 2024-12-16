import asyncio
import json
from datetime import datetime
from functools import partial
from secrets import token_hex

import aiohttp

import frappe
import frappe.defaults
from frappe.model.document import Document
from frappe.utils.dateutils import add_to_date


from ..doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    USER_DOCTYPE_NAME,
)
from ..utils import (
    build_datetime_from_string,
    build_headers,
    get_route_path,
    get_server_url,
    make_get_request,
    split_user_email,
    get_first_branch_id,
)
from .api_builder import EndpointsBuilder
from .remote_response_status_handlers import (
    customer_branch_details_submission_on_success,
    customer_insurance_details_submission_on_success,
    customer_search_on_success,
    imported_item_submission_on_success,
    imported_items_search_on_success,
    item_composition_submission_on_success,
    item_registration_on_success,
    notices_search_on_success,
    on_error,
    purchase_search_on_success,
    search_branch_request_on_success,
    stock_mvt_search_on_success,
    submit_inventory_on_success,
    user_details_submission_on_success,
)

endpoints_builder = EndpointsBuilder()


@frappe.whitelist()
def bulk_submit_sales_invoices(docs_list: str) -> None:
    from ..overrides.server.sales_invoice import on_submit

    data = json.loads(docs_list)
    all_sales_invoices = frappe.db.get_all(
        "Sales Invoice", {"docstatus": 1, "custom_successfully_submitted": 0}, ["name"]
    )

    for record in data:
        for invoice in all_sales_invoices:
            if record == invoice.name:
                doc = frappe.get_doc("Sales Invoice", record, for_update=False)
                on_submit(doc, method=None)


@frappe.whitelist()
def bulk_register_item(docs_list: str) -> None:
    data = json.loads(docs_list)
    all_items = frappe.db.get_all("Item", {"custom_item_registered": 0}, ["name"])
    for record in data:
        for item in all_items:
            if record == item.name:
                process_single_item(record)


@frappe.whitelist()
def process_single_item(record: str) -> None:
    """
    Process a single item for registration, construct the payload, and perform registration.
    
    Args:
        record (str): Name of the item to process.
    """
    item = frappe.get_doc("Item", record, for_update=False)
    
    valuation_rate = item.valuation_rate if item.valuation_rate is not None else 0

    request_data = {
        "name": item.name,
        "company_name": frappe.defaults.get_user_default("Company"),
        "itemCd": item.custom_item_code_etims,
        "itemClsCd": item.custom_item_classification,
        "itemTyCd": item.custom_product_type,
        "itemNm": item.item_name,
        "temStdNm": None,
        "orgnNatCd": item.custom_etims_country_of_origin_code,
        "pkgUnitCd": item.custom_packaging_unit_code,
        "qtyUnitCd": item.custom_unit_of_quantity_code,
        "taxTyCd": item.get("custom_taxation_type", "B"),
        "btchNo": None,
        "bcd": None,
        "dftPrc": round(valuation_rate, 2),
        "grpPrcL1": None,
        "grpPrcL2": None,
        "grpPrcL3": None,
        "grpPrcL4": None,
        "grpPrcL5": None,
        "addInfo": None,
        "sftyQty": None,
        "isrcAplcbYn": "Y",
        "useYn": "Y",
        "regrId": split_user_email(item.owner),
        "regrNm": item.owner,
        "modrId": split_user_email(item.modified_by),
        "modrNm": item.modified_by,
    }

    perform_item_registration(request_data=json.dumps(request_data))


@frappe.whitelist()
def perform_customer_search(request_data: str, vendor="OSCU KRA") -> None:
    """Search customer details in the eTims Server

    Args:
        request_data (str): Data received from the client
    """
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("CustSearchReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        payload = {"custmTin": data["tax_id"]}

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            customer_search_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            doctype="Customer",
            document_name=data["name"],
            job_name=f"{data['name']}_customer_search",
        )


@frappe.whitelist()
def perform_item_registration(request_data: str, vendor="OSCU KRA") -> dict | None:
    data: dict = json.loads(request_data)

    company_name = data.pop("company_name")

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("ItemSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = data
        endpoints_builder.success_callback = partial(
            item_registration_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            doctype="Item",
            document_name=data["name"],
            job_name=f"{data['name']}_register_item",
        )


@frappe.whitelist()
def send_insurance_details(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("BhfInsuranceSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        payload = {
            "isrccCd": data["insurance_code"],
            "isrccNm": data["insurance_name"],
            "isrcRt": round(data["premium_rate"], 0),
            "useYn": "Y",
            "regrNm": data["registration_id"],
            "regrId": split_user_email(data["registration_id"]),
            "modrNm": data["modifier_id"],
            "modrId": split_user_email(data["modifier_id"]),
        }

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            customer_insurance_details_submission_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            doctype="Customer",
            document_name=data["name"],
            job_name=f"{data['name']}_submit_insurance_information",
        )


@frappe.whitelist()
def send_branch_customer_details(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor),
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("BhfCustSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        payload = {
            "custNo": data["name"][:14],
            "custTin": data["customer_pin"],
            "custNm": data["customer_name"],
            "adrs": None,
            "telNo": None,
            "email": None,
            "faxNo": None,
            "useYn": "Y",
            "remark": None,
            "regrNm": data["registration_id"],
            "regrId": split_user_email(data["registration_id"]),
            "modrNm": data["modifier_id"],
            "modrId": split_user_email(data["modifier_id"]),
        }

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            customer_branch_details_submission_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            doctype="Customer",
            document_name=data["name"],
            job_name=f"{data['name']}_submit_customer_branch_details",
        )


@frappe.whitelist()
def save_branch_user_details(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)
    company_name = data["company_name"]
    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("BhfUserSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        payload = {
            "userId": data["user_id"],
            "userNm": data["full_names"],
            "pwd": "password",  # TODO: Find a fix for this
            "adrs": None,
            "cntc": None,
            "authCd": None,
            "remark": None,
            "useYn": "Y",
            "regrNm": data["registration_id"],
            "regrId": split_user_email(data["registration_id"]),
            "modrNm": data["modifier_id"],
            "modrId": split_user_email(data["modifier_id"]),
        }

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            user_details_submission_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            job_name=f"{data['name']}_send_branch_user_information",
            doctype=USER_DOCTYPE_NAME,
            document_name=data["name"],
        )


@frappe.whitelist()
def create_branch_user() -> None:
    # TODO: Implement auto-creation through background tasks
    present_users = frappe.db.get_all(
        "User", {"name": ["not in", ["Administrator", "Guest"]]}, ["name", "email"]
    )

    for user in present_users:
        doc = frappe.new_doc(USER_DOCTYPE_NAME)

        doc.system_user = user.email
        doc.branch_id = frappe.get_value(
            "Branch", {"custom_branch_code": "00"}, ["name"]
        )

        doc.save()

    frappe.msgprint("Inspect the Branches to make sure they are mapped correctly")


@frappe.whitelist()
def perform_item_search(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]
    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("ItemSearchReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        request_date = last_request_date.strftime("%Y%m%d%H%M%S")
        payload = {"lastReqDt": request_date}

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = lambda response: frappe.msgprint(
            f"{response}"
        )
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call(doctype="Item")


@frappe.whitelist()
def perform_import_item_search(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    if "branch_code" in data:
        headers = build_headers(company_name,vendor, data["branch_code"])
        server_url = get_server_url(company_name,vendor, data["branch_code"])

    else:
        headers = build_headers(company_name, vendor)
        server_url = get_server_url(company_name, vendor)

    route_path, last_request_date = get_route_path("ImportItemSearchReq")

    '''Use last_request_date as the last request date if it exists, else use the current date - 1 year'''
    if headers and server_url and route_path:
        request_date = add_to_date(datetime.now(), years=-1).strftime("%Y%m%d%H%M%S")
        last_request_date = last_request_date.strftime("%Y%m%d%H%M%S") or request_date
        url = f"{server_url}{route_path}"
        payload = {"lastReqDt": last_request_date}
        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = imported_items_search_on_success
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call()


@frappe.whitelist()
def perform_import_item_search_all_branches() -> None:
    all_credentials = frappe.get_all(
        SETTINGS_DOCTYPE_NAME,
        ["name", "bhfid", "communication_key", "tin", "company"],
    )

    for credential in all_credentials:
        request_data = json.dumps(
            {"company_name": credential.company, "branch_code": credential.bhfid}
        )

        perform_import_item_search(request_data)

@frappe.whitelist()
def perform_purchases_search(request_data: str, vendor: str="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("TrnsPurchaseSalesReq")

    if headers and server_url and route_path:
        request_date = last_request_date.strftime("%Y%m%d%H%M%S")

        url = f"{server_url}{route_path}"
        payload = {"lastReqDt": request_date}
        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = purchase_search_on_success
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call(
            doctype="Purchase Invoice",
        )


@frappe.whitelist()
def submit_inventory(request_data: str, vendor: str="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = frappe.defaults.get_user_default("Company")

    headers = build_headers(company_name,vendor, data["branch_id"])
    server_url = get_server_url(company_name,vendor, data["branch_id"])
    route_path, last_request_date = get_route_path("StockMasterSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        payload = {
            "itemCd": data["item_code"],
            "rsdQty": data["residual_qty"],
            "regrId": split_user_email(data["owner"]),
            "regrNm": data["owner"],
            "modrId": split_user_email(data["owner"]),
            "modrNm": data["owner"],
        }

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            submit_inventory_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            job_name=f"{data['name']}_submit_inventory",
            doctype="Stock Ledger Entry",
            document_name=data["name"],
        )


@frappe.whitelist()
def perform_item_classification_search(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("ItemClsSearchReq")

    if headers and server_url and route_path:
        request_date = last_request_date.strftime("%Y%m%d%H%M%S")

        url = f"{server_url}{route_path}"
        payload = {"lastReqDt": request_date}

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = lambda response: frappe.msgprint(
            f"{response}"
        )
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call(
            doctype="Item",
        )


@frappe.whitelist()
def search_branch_request(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("BhfSearchReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        request_date = last_request_date.strftime("%Y%m%d%H%M%S")

        payload = {"lastReqDt": "20240101000000"}

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = search_branch_request_on_success
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call(
            doctype="Branch",
        )


@frappe.whitelist()
def send_imported_item_request(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]
    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("ImportItemUpdateReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        declaration_date = build_datetime_from_string(
            data["declaration_date"], "%Y-%m-%d %H:%M:%S.%f"
        ).strftime("%Y%m%d")

        payload = {
            "taskCd": data["task_code"],
            "dclDe": declaration_date,
            "itemSeq": data["item_sequence"],
            "hsCd": data["hs_code"],
            "itemClsCd": data["item_classification_code"],
            "itemCd": data["item_code"],
            "imptItemSttsCd": data["import_item_status"],
            "remark": None,
            "modrNm": data["modified_by"],
            "modrId": split_user_email(data["modified_by"]),
        }

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = partial(
            imported_item_submission_on_success, document_name=data["name"]
        )
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            job_name=f"{data['name']}_submit_imported_item",
            doctype="Item",
            document_name=data["name"],
        )


@frappe.whitelist()
def perform_notice_search(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)

    route_path, last_request_date = get_route_path("NoticeSearchReq")
    request_date = add_to_date(datetime.now(), years=-1).strftime("%Y%m%d%H%M%S")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        payload = {"lastReqDt": request_date}

        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = notices_search_on_success
        endpoints_builder.error_callback = on_error

        endpoints_builder.make_remote_call(
            doctype=SETTINGS_DOCTYPE_NAME, document_name=data.get("name", None)
        )


@frappe.whitelist()
def perform_stock_movement_search(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name,vendor, data["branch_id"])
    server_url = get_server_url(company_name,vendor, data["branch_id"])

    route_path, last_request_date = get_route_path("StockMoveReq")
    request_date = last_request_date.strftime("%Y%m%d%H%M%S")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"
        payload = {"lastReqDt": request_date}
        endpoints_builder.headers = headers
        endpoints_builder.url = url
        endpoints_builder.payload = payload
        endpoints_builder.success_callback = stock_mvt_search_on_success
        endpoints_builder.error_callback = on_error

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            is_async=True,
            queue="default",
            timeout=300,
            job_name=token_hex(100),
        )

@frappe.whitelist()
def perform_stock_movement_search_all_branches() -> None:
    all_credentials = frappe.get_all(
        SETTINGS_DOCTYPE_NAME,
        ["name", "bhfid", "communication_key", "tin", "company"],
    )

    for credential in all_credentials:
        request_data = json.dumps(
            {"company_name": credential.company, "branch_id": credential.bhfid}
        )
        perform_stock_movement_search(request_data)

@frappe.whitelist()
def submit_item_composition(request_data: str, vendor="OSCU KRA") -> None:
    data: dict = json.loads(request_data)

    company_name = data["company_name"]

    headers = build_headers(company_name, vendor)
    server_url = get_server_url(company_name, vendor)
    route_path, last_request_date = get_route_path("SaveItemComposition")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        all_items = frappe.db.get_all("Item", ["*"])

        # Check if item to manufacture is registered before proceeding
        manufactured_item = frappe.get_value(
            "Item",
            {"name": data["item_name"]},
            ["custom_item_registered", "name"],
            as_dict=True,
        )

        if not manufactured_item.custom_item_registered:
            frappe.throw(
                f"Please register item: <b>{manufactured_item.name}</b> first to proceed.",
                title="Integration Error",
            )

        for item in data["items"]:
            for fetched_item in all_items:
                if item["item_code"] == fetched_item.item_code:
                    if fetched_item.custom_item_registered == 1:
                        payload = {
                            "itemCd": data["item_code"],
                            "cpstItemCd": fetched_item.custom_item_code_etims,
                            "cpstQty": item["qty"],
                            "regrId": split_user_email(data["registration_id"]),
                            "regrNm": data["registration_id"],
                        }

                        endpoints_builder.headers = headers
                        endpoints_builder.url = url
                        endpoints_builder.payload = payload
                        endpoints_builder.success_callback = partial(
                            item_composition_submission_on_success,
                            document_name=data["name"],
                        )
                        endpoints_builder.error_callback = on_error

                        frappe.enqueue(
                            endpoints_builder.make_remote_call,
                            is_async=True,
                            queue="default",
                            timeout=300,
                            job_name=f"{data['name']}_submit_item_composition",
                            doctype="BOM",
                            document_name=data["name"],
                        )

                    else:
                        frappe.throw(
                            f"""
                            Item: <b>{fetched_item.name}</b> is not registered.
                            <b>Ensure ALL Items are registered first to submit this composition</b>""",
                            title="Integration Error",
                        )


@frappe.whitelist()
def create_supplier_from_fetched_registered_purchases(request_data: str) -> None:
    data: dict = json.loads(request_data)

    new_supplier = create_supplier(data)

    frappe.msgprint(f"Supplier: {new_supplier.name} created")


def create_supplier(supplier_details: dict) -> Document:
    new_supplier = frappe.new_doc("Supplier")

    new_supplier.supplier_name = supplier_details["supplier_name"]
    new_supplier.tax_id = supplier_details["supplier_pin"]
    new_supplier.custom_supplier_branch = supplier_details["supplier_branch_id"]

    if "supplier_currency" in supplier_details:
        new_supplier.default_currency = supplier_details["supplier_currency"]

    if "supplier_nation" in supplier_details:
        new_supplier.country = supplier_details["supplier_nation"].capitalize()

    new_supplier.insert(ignore_if_duplicate=True)

    return new_supplier


@frappe.whitelist()
def create_items_from_fetched_registered_purchases(request_data: str) -> None:
    data = json.loads(request_data)
    if data["items"]:
        items = data["items"]
        for item in items:
            create_item(item)


def create_item(item: dict | frappe._dict) -> Document:
    item_code = item.get("item_code", None)
    
    new_item = frappe.new_doc("Item")
    new_item.is_stock_item = 0  # Default to 0
    new_item.item_code = item["item_name"]
    new_item.item_group = "All Item Groups"
    new_item.custom_item_classification = item["item_classification_code"]
    new_item.custom_packaging_unit = item["packaging_unit_code"]
    new_item.custom_unit_of_quantity = (
        item.get("quantity_unit_code", None) or item["unit_of_quantity_code"]
    )
    new_item.custom_taxation_type = item["taxation_type_code"]
    new_item.custom_etims_country_of_origin = (
        frappe.get_doc(
            COUNTRIES_DOCTYPE_NAME,
            {"code": item_code[:2]},
            for_update=False,
        ).name
        if item_code
        else None
    )
    new_item.custom_product_type = item_code[2:3] if item_code else None

    if item_code and int(item_code[2:3]) != 3:
        new_item.is_stock_item = 1
    else:
        new_item.is_stock_item = 0

    new_item.custom_item_code_etims = item["item_code"]
    new_item.valuation_rate = item["unit_price"]

    if "imported_item" in item:
        new_item.is_stock_item = 1
        new_item.custom_referenced_imported_item = item["imported_item"]

    new_item.insert(ignore_mandatory=True, ignore_if_duplicate=True)
    if new_item.custom_item_classification is not None:
        process_single_item(new_item.name)
    return new_item


@frappe.whitelist()
def create_purchase_invoice_from_request(request_data: str) -> None:
    data = json.loads(request_data)
    bhfId=get_first_branch_id()
    # Check if supplier exists
    supplier = None
    if not frappe.db.exists("Supplier", data["supplier_name"], cache=False):
        supplier = create_supplier(data).name

    all_items = []
    all_existing_items = {
        item["name"]: item for item in frappe.db.get_all("Item", ["*"])
    }

    for received_item in data["items"]:
        # Check if item exists
        if received_item["item_name"] not in all_existing_items:
            created_item = create_item(received_item)
            all_items.append(created_item)

    # Create the Purchase Invoice
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.supplier = supplier or data["supplier_name"]
    purchase_invoice.update_stock = 1
    purchase_invoice.custom_supplier_branch_id = data["supplier_branch_id"]
    purchase_invoice.bill_no = data["supplier_invoice_no"]
    purchase_invoice.bill_date = data["supplier_invoice_date"]
    purchase_invoice.branch = bhfId
    if "currency" in data:
        # The "currency" key is only available when creating from Imported Item
        purchase_invoice.currency = data["currency"]
        purchase_invoice.custom_source_registered_imported_item = data["name"]
    else:
        purchase_invoice.custom_source_registered_purchase = data["name"]

    if "exchange_rate" in data:
        purchase_invoice.conversion_rate = data["exchange_rate"]

    purchase_invoice.set("items", [])

    # TODO: Remove Hard-coded values
    purchase_invoice.custom_purchase_type = "Copy"
    purchase_invoice.custom_receipt_type = "Purchase"
    purchase_invoice.custom_payment_type = "CASH"
    purchase_invoice.custom_purchase_status = "Approved"

    company_abbr = frappe.get_value(
        "Company", {"name": frappe.defaults.get_user_default("Company")}, ["abbr"]
    )
    expense_account = frappe.db.get_value(
        "Account",
        {
            "name": [
                "like",
                f"%Cost of Goods Sold%{company_abbr}",
            ]
        },
        ["name"],
    )

    for item in data["items"]:
        purchase_invoice.append(
            "items",
            {
                "item_name": item["item_name"],
                "item_code": item["item_name"],
                "qty": item["quantity"],
                "rate": item["unit_price"],
                "expense_account": expense_account,
                "custom_item_classification": item["item_classification_code"],
                "custom_packaging_unit": item["packaging_unit_code"],
                "custom_unit_of_quantity": item["quantity_unit_code"],
                "custom_taxation_type": item["taxation_type_code"],
                "task_code": item.get("task_code", ''),
},
        )
    validate_mapping_and_registration_of_items(data["items"])
    purchase_invoice.insert(ignore_mandatory=True)

    frappe.msgprint("Purchase Invoices have been created")

@frappe.whitelist()
def ping_server(request_data: str) -> None:
    url = json.loads(request_data)["server_url"]

    try:
        response = asyncio.run(make_get_request(url))

        if len(response) == 13:
            frappe.msgprint("The Server is Online")
            return

        frappe.msgprint("The Server is Offline")
        return

    except aiohttp.client_exceptions.ClientConnectorError:
        frappe.msgprint("The Server is Offline")
        return


@frappe.whitelist()
def create_stock_entry_from_stock_movement(request_data: str) -> None:
    data = json.loads(request_data)

    for item in data["items"]:
        if not frappe.db.exists("Item", item["item_name"], cache=False):
            # Create item if item doesn't exist
            create_item(item)

    # Create stock entry
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Transfer"

    stock_entry.set("items", [])

    source_warehouse = frappe.get_value(
        "Warehouse",
        {"custom_branch": data["branch_id"]},
        ["name"],
        as_dict=True,
    )

    target_warehouse = frappe.get_value(
        "Warehouse",
        {"custom_branch": "01"},  # TODO: Fix hardcode from 01 to a general solution
        ["name"],
        as_dict=True,
    )

    for item in data["items"]:
        stock_entry.append(
            "items",
            {
                "s_warehouse": source_warehouse.name,
                "t_warehouse": target_warehouse.name,
                "item_code": item["item_name"],
                "qty": item["quantity"],
            },
        )

    stock_entry.save()

    frappe.msgprint(f"Stock Entry {stock_entry.name} created successfully")

def validate_mapping_and_registration_of_items(items):
    for item in items:
        task_code = item.get("task_code") or item.get("item_name")
        items = frappe.get_all("Item", 
		filters={"custom_referenced_imported_item": task_code}, 
		fields=["name","item_name","item_code"]
	)
        if items:
            item_name = items[0].name
            from kenya_compliance.kenya_compliance.overrides.server.purchase_invoice import validation_message
            validation_message(item_name)
        