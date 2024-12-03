# Copyright (c) 2024, Navari Ltd and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ..doctype_names_mapping import COUNTRIES_DOCTYPE_NAME


class TestNavarieTimsCountry(FrappeTestCase):
    def test_country_creation(self) -> None:
        country_name = "The Lands Between"

        doc = frappe.new_doc(COUNTRIES_DOCTYPE_NAME)

        doc.code = "TEST"
        doc.sort_order = "0"
        doc.code_name = country_name
        doc.code_description = country_name

        doc.save()

        fetched_doc = frappe.get_doc(COUNTRIES_DOCTYPE_NAME, doc.name, for_update=False)

        self.assertEqual(fetched_doc.name, country_name)
        self.assertEqual(fetched_doc.code, "TEST")
        self.assertEqual(fetched_doc.code_name, country_name)
        self.assertEqual(fetched_doc.code_description, country_name)

    def test_duplicate_country_creation(self) -> None:
        with self.assertRaises(frappe.DuplicateEntryError):
            country_name = "Test Country"
            doc = frappe.new_doc(COUNTRIES_DOCTYPE_NAME)

            doc.code = "TEST"
            doc.sort_order = "0"
            doc.code_name = country_name
            doc.code_description = country_name

            doc.save()

            doc = frappe.new_doc(COUNTRIES_DOCTYPE_NAME)

            doc.code = "TEST2"
            doc.sort_order = "0"
            doc.code_name = country_name
            doc.code_description = country_name

            doc.save()
