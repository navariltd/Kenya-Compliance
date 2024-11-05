from functools import partial
from hashlib import sha256
from typing import Literal

import frappe
from frappe.model.document import Document
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data

from ...apis.api_builder import EndpointsBuilder
from ...apis.remote_response_status_handlers import (
    on_error,
    stock_mvt_submission_on_success,
)
from ...utils import (
    build_headers,
    extract_document_series_number, 
    get_route_path,
    get_server_url,
    split_user_email,
)

endpoints_builder = EndpointsBuilder()


def on_update(doc: Document, method: str | None = None) -> None:
    company_name = doc.company
    all_items = frappe.db.get_all(
        "Item", ["*"]
    )  # Get all items to filter and fetch metadata 
    record = frappe.get_doc(doc.voucher_type, doc.voucher_no)
    series_no = extract_document_series_number(record)
    payload = {
        "sarNo": series_no,
        "orgSarNo": series_no,
        "regTyCd": "M",
        "custTin": None,
        "custNm": None,
        "custBhfId": get_warehouse_branch_id(doc.get('warehouse')) or None,
        "ocrnDt": record.posting_date.strftime("%Y%m%d"),
        "totTaxblAmt": 0,
        "totItemCnt": len(record.items),
        "totTaxAmt": 0,
        "totAmt": 0,
        "remark": None,
        "regrId": split_user_email(record.owner),
        "regrNm": record.owner,
        "modrNm": record.modified_by,
        "modrId": split_user_email(record.modified_by),
    }
    try:
        headers = build_headers(company_name, record.branch)
    except Exception as e:
        frappe.log_error(message=str(e), title="Header Building Error")
        headers = {
            "tin": "",
            "bhfId": "",
            "cmcKey": "",
            "Content-Type": "application/json",
        }

    if doc.voucher_type == "Stock Reconciliation":
        items_list = get_stock_recon_movement_items_details(
            record.items, all_items
        )  # Get details abt item using the function
        current_item = list(
            filter(lambda item: item["itemNm"] == doc.item_code, items_list)
        )  # filter only the item referenced in this stock ledger entry
        qty_diff = int(
            current_item[0].pop("quantity_difference")
        )  # retrieve the quantity difference from the items dict. Only applies to stock recons
        payload["itemList"] = current_item
        payload["totItemCnt"] = len(current_item)

        if record.purpose == "Opening Stock":
            # Stock Recons of type "opening stock" are never negative, so just short-curcuit
            payload["sarTyCd"] = "06"

        else:
            # Stock recons of other types apart from "opening stock"
            if qty_diff < 0:
                # If the quantity difference is negative, apply etims stock in/out code 16
                payload["sarTyCd"] = "16"

            else:
                # If the quantity difference is positive, apply etims stock in/out code 06
                payload["sarTyCd"] = "06"

    if doc.voucher_type == "Stock Entry":
        items_list = get_stock_entry_movement_items_details(record.items, all_items)
        current_item = [item for item in items_list if item["itemNm"] in [i.item_code for i in doc.items]]

        payload["itemList"] = current_item
        payload["totItemCnt"] = len(current_item)

        if record.stock_entry_type == "Material Receipt":
            payload["sarTyCd"] = "04"

        if record.stock_entry_type == "Material Transfer":
            doc_warehouse_branch_id = get_warehouse_branch_id(doc.warehouse)
            voucher_details = frappe.db.get_value(
                "Stock Entry Detail",
                {"name": doc.voucher_detail_no},
                ["s_warehouse", "t_warehouse"],
                as_dict=True,
            )

            if doc.actual_qty < 0:
                # If the record warehouse is the source warehouse
                headers = build_headers(doc.company, doc_warehouse_branch_id)
                payload["custBhfId"] = get_warehouse_branch_id(
                    voucher_details.t_warehouse
                )
                payload["sarTyCd"] = "13"

            else:
                # If the record warehouse is the target warehouse
                headers = build_headers(doc.company, doc_warehouse_branch_id)
                payload["custBhfId"] = get_warehouse_branch_id(
                    voucher_details.s_warehouse
                )
                payload["sarTyCd"] = "04"

        if record.stock_entry_type == "Manufacture":
            if doc.actual_qty > 0:
                payload["sarTyCd"] = "05"

            else:
                payload["sarTyCd"] = "14"

        if record.stock_entry_type in ("Send to Subcontractor", "Material Issue"):
            payload["sarTyCd"] = "13"

        if record.stock_entry_type == "Repack":
            if doc.actual_qty < 0:
                # Negative repack
                payload["sarTyCd"] = "14"

            else:
                payload["sarTyCd"] = "05"

    if doc.voucher_type in ("Purchase Receipt", "Purchase Invoice"):
        # TODO: This is very bad looking. Clean it up
        items_list = get_purchase_docs_items_details(record.items, all_items)
        item_taxes = get_itemised_tax_breakup_data(record)

        current_item = list(
            filter(lambda item: item["itemNm"] == doc.item_code, items_list)
        )
        tax_details = list(filter(lambda i: i["item"] == doc.item_code, item_taxes))[0]

        current_item[0]["taxblAmt"] = round(
            tax_details["taxable_amount"] / current_item[0]["qty"], 2
        )
        current_item[0]["totAmt"] = round(
            tax_details["taxable_amount"] / current_item[0]["qty"], 2
        )

        actual_tax_amount = 0
        tax_head = doc.taxes[0].description

        actual_tax_amount = tax_details[tax_head]["tax_amount"]

        current_item[0]["taxAmt"] = round(actual_tax_amount / current_item[0]["qty"], 2)

        payload["itemList"] = current_item
        payload["totItemCnt"] = len(current_item)

        # TODO: use qty change field from SLE
        if record.is_return:
            payload["sarTyCd"] = "12"

        else:
            if current_item[0]["is_imported_item"]:
                payload["sarTyCd"] = "01"

            else:
                payload["sarTyCd"] = "02"

    if doc.voucher_type in ("Delivery Note", "Sales Invoice"):
        if (
            doc.voucher_type == "Sales Invoice"
            and record.custom_successfully_submitted != 1
        ):
            return

        items_list = get_notes_docs_items_details(record.items, all_items)
        item_taxes = get_itemised_tax_breakup_data(record)

        current_item = list(
            filter(lambda item: item["itemNm"] == doc.item_code, items_list)
        )  # Get current item only
        tax_details = list(filter(lambda i: i["item"] == doc.item_code, item_taxes))[
            0
        ]  # filter current items tax details

        current_item[0]["taxblAmt"] = round(
            tax_details["taxable_amount"] / current_item[0]["qty"], 2
        )  # calculate taxable amt
        current_item[0]["totAmt"] = round(
            tax_details["taxable_amount"] / current_item[0]["qty"], 2
        )  # calculate total amt

        actual_tax_amount = 0
        tax_head = doc.taxes[0].description

        actual_tax_amount = tax_details[tax_head]["tax_amount"]

        current_item[0]["taxAmt"] = round(
            actual_tax_amount / current_item[0]["qty"], 2
        )  # calculate tax amt

        payload["itemList"] = current_item
        payload["totItemCnt"] = len(current_item)
        payload["custNm"] = record.customer
        payload["custTin"] = record.tax_id

        # TODO: opposite of previous, and use qty change field
        # TODO: These map to sales returns
        if record.is_return:
            # if is_return is checked, it turns to different type of docs
            if doc.actual_qty > 0:
                payload["sarTyCd"] = "03"

            else:
                payload["sarTyCd"] = "11"

        else:
            payload["sarTyCd"] = "11"


    try:
        server_url = get_server_url(company_name, record.branch) 
    except Exception as e:
        frappe.log_error(message=str(e), title="Header Building Error")
        server_url = "https://etims-api-sbx.kra.go.ke/etims-api" 
    
    route_path, last_request_date = get_route_path("StockIOSaveReq")

    if headers and server_url and route_path:
        url = f"{server_url}{route_path}"

        endpoints_builder.url = url
        endpoints_builder.headers = headers
        endpoints_builder.payload = payload
        endpoints_builder.error_callback = on_error
        endpoints_builder.success_callback = partial(
            stock_mvt_submission_on_success, document_name=doc.name
        )

        job_name = sha256(
            f"{doc.name}{doc.creation}{doc.modified}".encode(), usedforsecurity=False
        ).hexdigest()

        frappe.enqueue(
            endpoints_builder.make_remote_call,
            queue="default",
            is_async=True,
            timeout=300,
            job_name=job_name,
            doctype="Stock Ledger Entry",
            document_name=doc.name,
        )


def get_stock_entry_movement_items_details(
    records: list[Document], all_items: list[Document]
) -> list[dict]:
    items_list = []

    for i in records:
        try:
            item = frappe.get_doc("Item", i["item_code"])
            prc =  round(int(i["basic_rate"]), 2) if i["basic_rate"] else 0
            qty = abs(i["qty"])
        except AttributeError:
            prc =  round(int(item.basic_rate), 2) if item.basic_rate else 0
            qty = abs(item.qty)
        for fetched_item in all_items:
            if item.item_code == fetched_item.name:
                items_list.append(
                    {
                        "itemSeq": item.idx,
                        "itemCd": fetched_item.custom_item_code_etims,
                        "itemClsCd": fetched_item.custom_item_classification,
                        "itemNm": fetched_item.item_code,
                        "bcd": None,
                        "pkgUnitCd": fetched_item.custom_packaging_unit_code,
                        "pkg": 1,
                        "qtyUnitCd": fetched_item.custom_unit_of_quantity_code,
                        "qty": qty,
                        "itemExprDt": "",
                        "prc": prc,
                        "splyAmt": prc,
                        # TODO: Handle discounts properly
                        "totDcAmt": 0,
                        "taxTyCd": fetched_item.custom_taxation_type or "B",
                        "taxblAmt": 0,
                        "taxAmt": 0,
                        "totAmt": 0,
                    }
                )

    return items_list


def get_stock_recon_movement_items_details(
    records: list, all_items: list
) -> list[dict]:
    items_list = []
    # current_qty

    for i in records:
        try:
            item = frappe.get_doc("Item", i["item_code"])
            prc =  round(int(i["valuation_rate"]), 2) if i["valuation_rate"] else 0
            qty = abs(int(i["quantity_difference"]))
        except AttributeError:
            prc =  round(int(item.valuation_rate), 2) if item.valuation_rate else 0
            qty = abs(item.quantity_difference)
        for fetched_item in all_items:
            if item.item_code == fetched_item.name:
                items_list.append(
                    {
                        "itemSeq": item.idx,
                        "itemCd": fetched_item.custom_item_code_etims,
                        "itemClsCd": fetched_item.custom_item_classification,
                        "itemNm": fetched_item.item_code,
                        "bcd": None,
                        "pkgUnitCd": fetched_item.custom_packaging_unit_code,
                        "pkg": 1,
                        "qtyUnitCd": fetched_item.custom_unit_of_quantity_code,
                        "qty": qty,
                        "itemExprDt": "",
                        "prc": prc,
                        "splyAmt": prc,
                        "totDcAmt": 0,
                        "taxTyCd": fetched_item.custom_taxation_type or "B",
                        "taxblAmt": 0,
                        "taxAmt": 0,
                        "totAmt": 0,
                        "quantity_difference": i["quantity_difference"],
                    }
                )

    return items_list


def get_purchase_docs_items_details(
    items: list, all_present_items: list[Document]
) -> list[dict]:
    items_list = []

    for i in items:
        try:
            item = frappe.get_doc("Item", i["item_code"])
            prc =  round(int(i["valuation_rate"]), 2) if i["valuation_rate"] else 0
            qty = abs(i["qty"])
        except AttributeError:
            prc =  round(int(item.valuation_rate), 2) if item.valuation_rate else 0
            qty = abs(item.qty)
        for fetched_item in all_present_items:
            if item.item_code == fetched_item.name:
                items_list.append(
                    {
                        "itemSeq": item.idx,
                        "itemCd": fetched_item.custom_item_code_etims,
                        "itemClsCd": fetched_item.custom_item_classification,
                        "itemNm": fetched_item.item_code,
                        "bcd": None,
                        "pkgUnitCd": fetched_item.custom_packaging_unit_code,
                        "pkg": 1,
                        "qtyUnitCd": fetched_item.custom_unit_of_quantity_code,
                        "qty": qty,
                        "itemExprDt": "",
                        "prc": prc,
                        "splyAmt": prc,
                        "totDcAmt": 0,
                        "taxTyCd": fetched_item.custom_taxation_type or "B",
                        "taxblAmt": 0,
                        "taxAmt": 0,
                        "totAmt": 0,
                        "is_imported_item": (
                            True
                            if (
                                fetched_item.custom_imported_item_status
                                and fetched_item.custom_imported_item_task_code
                            )
                            else False
                        ),
                    }
                )

    return items_list 


def get_notes_docs_items_details(
    items: list[Document], all_present_items: list[Document]
) -> list[dict]:
    items_list = []

    for i in items:
        try:
            item = frappe.get_doc("Item", i["item_code"])
            prc =  round(int(i["base_net_rate"]), 2) if i["base_net_rate"] else 0
            qty = abs(i["qty"])
        except AttributeError:
            prc =  round(int(item.basic_rate), 2) if item.basic_rate else 0
            qty = abs(item.qty)
        for fetched_item in all_present_items:
            if item.item_code == fetched_item.name:
                items_list.append(
                    {
                        "itemSeq": item.idx,
                        "itemCd": None,
                        "itemClsCd": fetched_item.custom_item_classification,
                        "itemNm": fetched_item.item_code,
                        "bcd": None,
                        "pkgUnitCd": fetched_item.custom_packaging_unit_code,
                        "pkg": 1,
                        "qtyUnitCd": fetched_item.custom_unit_of_quantity_code,
                        "qty": qty,
                        "itemExprDt": "",
                        "prc": prc,
                        "splyAmt": prc,
                        "totDcAmt": 0,
                        "taxTyCd": fetched_item.custom_taxation_type or "B",
                        "taxblAmt": 0,
                        "taxAmt": 0,
                        "totAmt": 0,
                    }
                )

    return items_list


def get_warehouse_branch_id(warehouse_name: str) -> str | Literal[0]:
    try:
        branch_id = frappe.db.get_value(
            "Warehouse", {"name": warehouse_name}, ["custom_branch"], as_dict=True
        )

        if branch_id:
            return branch_id.custom_branch
    except:
        pass

    return 0
