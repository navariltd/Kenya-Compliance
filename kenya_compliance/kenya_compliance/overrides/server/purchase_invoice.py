from collections import defaultdict
from functools import partial

import frappe
from frappe.model.document import Document
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data

from ...apis.api_builder import EndpointsBuilder
from ...apis.remote_response_status_handlers import (
    on_error,
    purchase_invoice_submission_on_success,
)
from ...utils import (
    build_headers,
    extract_document_series_number,
    get_route_path,
    get_server_url,
    quantize_number,
    split_user_email,
)
from .shared_overrides import update_tax_breakdowns

endpoints_builder = EndpointsBuilder()


def validate(doc: Document, method: str) -> None:
    item_taxes = get_itemised_tax_breakup_data(doc)

    taxes_breakdown = defaultdict(list)
    taxable_breakdown = defaultdict(list)
    if not doc.taxes:
        vat_acct = frappe.get_value(
            "Account", {"account_type": "Tax", "tax_rate": "16"}, ["name"], as_dict=True
        )
        doc.set(
            "taxes",
            [
                {
                    "account_head": vat_acct.name,
                    "included_in_print_rate": 1,
                    "description": vat_acct.name.split("-", 1)[0].strip(),
                    "category": "Total",
                    "add_deduct_tax": "Add",
                    "charge_type": "On Net Total",
                }
            ],
        )

    else:
        tax_head = doc.taxes[0].description
        for index, item in enumerate(doc.items):
            taxes_breakdown[item.custom_taxation_type].append(
                item_taxes[index][tax_head]["tax_amount"]
            )
            taxable_breakdown[item.custom_taxation_type].append(
                item_taxes[index]["taxable_amount"]
            )

        update_tax_breakdowns(doc, (taxes_breakdown, taxable_breakdown))


def on_submit(doc: Document, method: str) -> None:
    if doc.is_return == 0 and doc.update_stock == 1:
        # TODO: Handle cases when item tax templates have not been picked
        company_name = doc.company

        headers = build_headers(company_name, doc.branch)
        server_url = get_server_url(company_name, doc.branch)
        route_path, last_request_date = get_route_path("TrnsPurchaseSaveReq")

        if headers and server_url and route_path:
            url = f"{server_url}{route_path}"
            payload = build_purchase_invoice_payload(doc)

            endpoints_builder.url = url
            endpoints_builder.headers = headers
            endpoints_builder.payload = payload
            endpoints_builder.success_callback = partial(
                purchase_invoice_submission_on_success, document_name=doc.name
            )

            endpoints_builder.error_callback = on_error

            frappe.enqueue(
                endpoints_builder.make_remote_call,
                is_async=True,
                queue="default",
                timeout=300,
                job_name=f"{doc.name}_send_purchase_information",
                doctype="Purchase Invoice",
                document_name=doc.name,
            )


def build_purchase_invoice_payload(doc: Document) -> dict:
    series_no = extract_document_series_number(doc)
    items_list = get_items_details(doc)

    payload = {
        "invcNo": series_no,
        "orgInvcNo": 0,
        "spplrTin": doc.tax_id,
        "spplrBhfId": doc.custom_supplier_branch_id,
        "spplrNm": doc.supplier,
        "spplrInvcNo": doc.bill_no,
        "regTyCd": "A",
        "pchsTyCd": doc.custom_purchase_type_code,
        "rcptTyCd": doc.custom_receipt_type_code,
        "pmtTyCd": doc.custom_payment_type_code,
        "pchsSttsCd": doc.custom_purchase_status_code,
        "cfmDt": None,
        "pchsDt": "".join(str(doc.posting_date).split("-")),
        "wrhsDt": None,
        "cnclReqDt": "",
        "cnclDt": "",
        "rfdDt": None,
        "totItemCnt": len(items_list),
        "taxblAmtA": doc.custom_taxbl_amount_a or 0,
        "taxblAmtB": doc.custom_taxbl_amount_b or 0,
        "taxblAmtC": doc.custom_taxbl_amount_c or 0,
        "taxblAmtD": doc.custom_taxbl_amount_d or 0,
        "taxblAmtE": doc.custom_taxbl_amount_e or 0,
        "taxRtA": 0,
        "taxRtB": 16 if doc.custom_tax_b else 0,
        "taxRtC": 0,
        "taxRtD": 0,
        "taxRtE": 8 if doc.custom_tax_e else 0,
        "taxAmtA": doc.custom_tax_a or 0,
        "taxAmtB": doc.custom_tax_b or 0,
        "taxAmtC": doc.custom_tax_c or 0,
        "taxAmtD": doc.custom_tax_d or 0,
        "taxAmtE": doc.custom_tax_e or 0,
        "totTaxblAmt": quantize_number(doc.base_net_total),
        "totTaxAmt": quantize_number(doc.total_taxes_and_charges),
        "totAmt": quantize_number(doc.grand_total),
        "remark": None,
        "regrNm": doc.owner,
        "regrId": split_user_email(doc.owner),
        "modrNm": doc.modified_by,
        "modrId": split_user_email(doc.modified_by),
        "itemList": items_list,
    }

    return payload


def get_items_details(doc: Document) -> list:
    items_list = []
    item_taxes = get_itemised_tax_breakup_data(doc)

    for index, item in enumerate(doc.items):
        try:
            taxable_amount = item_taxes[index]["taxable_amount"]
        except IndexError as e:
            frappe.throw(
                "Please ensure tax templates are supplied as required for <b>each item, and/or in the Purchase taxes and charges table</b>",
                e,
                "Validation Error",
            )

        actual_tax_amount = 0
        tax_head = doc.taxes[0].description  # Fetch tax head from taxes table

        actual_tax_amount = item_taxes[index][tax_head]["tax_amount"]

        tax_amount = actual_tax_amount

        items_list.append(
            {
                "itemSeq": item.idx,
                "itemCd": item.custom_item_code_etims,
                "itemClsCd": item.custom_item_classification_code,
                "itemNm": item.item_name,
                "bcd": "",
                "spplrItemClsCd": None,
                "spplrItemCd": None,
                "spplrItemNm": None,
                "pkgUnitCd": item.custom_packaging_unit_code,
                "pkg": 1,
                "qtyUnitCd": item.custom_unit_of_quantity_code,
                "qty": abs(item.qty),
                "prc": item.base_rate,
                "splyAmt": item.base_amount,
                "dcRt": quantize_number(item.discount_percentage) or 0,
                "dcAmt": quantize_number(item.discount_amount) or 0,
                "taxblAmt": quantize_number(item.net_amount),
                "taxTyCd": item.custom_taxation_type or "B",
                "taxAmt": quantize_number(item.custom_tax_amount) or 0,
                "totAmt": quantize_number(item.net_amount + item.custom_tax_amount),
                "itemExprDt": None,
            }
        )

    return items_list
