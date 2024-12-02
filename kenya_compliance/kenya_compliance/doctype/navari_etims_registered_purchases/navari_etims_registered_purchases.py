# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NavarieTimsRegisteredPurchases(Document):
    pass
import json
import frappe

@frappe.whitelist()
def validate_item_mapped_and_registered(items):
    '''I dont think this method will work
    Reason: We have item with same item name which is used as item code during creation of item,
    but they have different item classification'''
    try:
        items = json.loads(items)

        for item in items:            
            similar_items = frappe.get_all(
                "Item",
                filters={
                    "item_name": item.get("item_name"),
                    "item_code": item.get("item_name"),
                    # "custom_item_classification": item.get("item_classification_code"),
                    #"custom_item_code_etims":item.get("item_code"),
                    "custom_taxation_type": item.get("taxation_type_code"),
                },
                fields=["name", "item_name", "item_code"],
            )
            if not similar_items:
                frappe.response["message"] = False
                return

        frappe.response["message"] = True
    except Exception as e:
        frappe.log_error(f"Error validating items: {str(e)}")
        