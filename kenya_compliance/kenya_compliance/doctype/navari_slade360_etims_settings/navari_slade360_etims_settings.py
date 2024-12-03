# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NavariSlade360eTimsSettings(Document):
    def validate(self):
        if self.is_active == 1:
            print(self)
            existing_doc = frappe.db.exists(
                "Navari Slade360 eTims Settings",
                {
                    "bhfid": self.bhfid,
                    "company": self.company,
                    "is_active": 1,
                    "name": ("!=", self.name),
                },
            )

            if existing_doc:
                frappe.throw(
                    f"Only one active setting is allowed for bhfid '{self.bhfid}' and company '{self.company}'."
                )
