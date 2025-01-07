import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    frappe.delete_doc("Custom Field", "Purchase Invoice Item-task_code", force=True)


    custom_fields = {
        "Purchase Invoice Item": [
            {
                "fieldname": "task_code",
                "fieldtype": "Link",
                "options": "Navari eTims Registered Imported Item",
                "label": "Task Code",
                "translatable": 1,
                "insert_after": "sales_invoice_item"
            },
           
        ]
    }

    create_custom_fields(custom_fields, update=True)