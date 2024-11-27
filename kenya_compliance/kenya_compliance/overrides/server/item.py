import json

import deprecation

import frappe
import frappe.defaults
from frappe.model.document import Document

from .... import __version__
from ...apis.apis import perform_item_registration
from ...utils import split_user_email
from frappe import _


@deprecation.deprecated(
    deprecated_in="0.6.2",
    removed_in="1.0.0",
    current_version=__version__,
    details="Use the Register Item button in Item record",
)
def before_insert(doc: Document, method: str) -> None:
    """Item doctype before insertion hook"""

    item_registration_data = {
        "name": doc.name,
        "company_name": frappe.defaults.get_user_default("Company"),
        "itemCd": doc.custom_item_code_etims,
        "itemClsCd": doc.custom_item_classification,
        "itemTyCd": doc.custom_product_type,
        "itemNm": doc.item_name,
        "temStdNm": None,
        "orgnNatCd": doc.custom_etims_country_of_origin_code,
        "pkgUnitCd": doc.custom_packaging_unit_code,
        "qtyUnitCd": doc.custom_unit_of_quantity_code,
        "taxTyCd": ("B" if not doc.custom_taxation_type else doc.custom_taxation_type),
        "btchNo": None,
        "bcd": None,
        "dftPrc": doc.valuation_rate,
        "grpPrcL1": None,
        "grpPrcL2": None,
        "grpPrcL3": None,
        "grpPrcL4": None,
        "grpPrcL5": None,
        "addInfo": None,
        "sftyQty": None,
        "isrcAplcbYn": "Y",
        "useYn": "Y",
        "regrId": split_user_email(doc.owner),
        "regrNm": doc.owner,
        "modrId": split_user_email(doc.modified_by),
        "modrNm": doc.modified_by,
    }

    perform_item_registration(json.dumps(item_registration_data))


# def validate(doc: Document, method: str) -> None:
#     # FIXME Ensure all item code numbers follow a global serial
#     # FIXME Currently, the item code number for each item is incremented if there's an item with same etims item code value
#     if not doc.custom_item_registered or "None" in doc.custom_item_code_etims:
#         # Check if Item code contains None or if it's not present
#         item_code = f"{doc.custom_etims_country_of_origin_code}{doc.custom_product_type}{doc.custom_packaging_unit_code}{doc.custom_unit_of_quantity_code}"
#         count = frappe.db.count(
#             "Item", {"custom_item_code_etims": ["like", f"{item_code}%"]}
#         )

#         doc.custom_item_code_etims = f"{item_code}{str(count + 1).zfill(7)}"

#     is_tax_type_changed = doc.has_value_changed(
#         "custom_taxation_type"
#     )  # Check if tax type field changed
#     if doc.custom_taxation_type and is_tax_type_changed:
#         relevant_tax_templates = frappe.get_all(
#             "Item Tax Template",
#             ["*"],
#             {
#                 "custom_etims_taxation_type": doc.custom_taxation_type,
#             },
#         )

#         if relevant_tax_templates:
#             doc.set("taxes", [])
#             for template in relevant_tax_templates:
#                 doc.append("taxes", {"item_tax_template": template.name})


def validate(doc: Document, method: str) -> None:
    
    new_prefix = f"{doc.custom_etims_country_of_origin_code}{doc.custom_product_type}{doc.custom_packaging_unit_code}{doc.custom_unit_of_quantity_code}"
    
    # Check if custom_item_code_etims exists and extract its suffix if so
    if doc.custom_item_code_etims:
        # Extract the last 7 digits as the suffix
        existing_suffix = doc.custom_item_code_etims[-7:]
    else:
        # If there is no existing code, generate a new suffix
        last_code = frappe.db.sql(
            """
            SELECT custom_item_code_etims 
            FROM `tabItem`
            WHERE custom_item_classification = %s
            ORDER BY CAST(SUBSTRING(custom_item_code_etims, -7) AS UNSIGNED) DESC
            LIMIT 1
            """,
            (doc.custom_item_classification,),
            as_dict=True,
        )

        if last_code:
            last_suffix = int(last_code[0]["custom_item_code_etims"][-7:])
            existing_suffix = str(last_suffix + 1).zfill(7)
        else:
            # Start from '0000001' if no matching classification item exists
            existing_suffix = "0000001"

    # Combine the new prefix with the existing or new suffix
    doc.custom_item_code_etims = f"{new_prefix}{existing_suffix}"

    # Check if the tax type field has changed
    is_tax_type_changed = doc.has_value_changed("custom_taxation_type")
    if doc.custom_taxation_type and is_tax_type_changed:
        relevant_tax_templates = frappe.get_all(
            "Item Tax Template",
            ["*"],
            {"custom_etims_taxation_type": doc.custom_taxation_type},
        )

        if relevant_tax_templates:
            doc.set("taxes", [])
            for template in relevant_tax_templates:
                doc.append("taxes", {"item_tax_template": template.name})

@frappe.whitelist()
def prevent_item_deletion(doc, method):
    if doc.custom_item_registered == 1:  # Assuming 1 means registered, adjust as needed
        frappe.throw(_("Cannot delete registered items"))