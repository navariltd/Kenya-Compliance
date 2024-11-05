# Copyright (c) 2024, Navari Ltd and Contributors
# See license.txt

from unittest.mock import patch
import frappe
from frappe.model.delete_doc import delete_doc
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase

from ..doctype_names_mapping import (
    PRODUCTION_SERVER_URL,
    SANDBOX_SERVER_URL,
    SETTINGS_DOCTYPE_NAME,
)
from .navari_kra_etims_settings import NavariKRAeTimsSettings
from ...background_tasks.tasks import send_sales_invoices_information


def mock_before_insert(*args) -> None:
    pass


def mock_before_insert_2(self, *args) -> None:
    if self.autocreate_branch_dimension and self.is_active:
        if frappe.db.exists("Accounting Dimension", "Branch", cache=False):
            return

        dimension = frappe.new_doc("Accounting Dimension")
        dimension.document_type = "Branch"

        dimension.set("dimension_defaults", [])

        dimension.append(
            "dimension_defaults",
            {
                "company": "Compliance Test Company",
            },
        )

        dimension.save()


def create_test_company():
    frappe.delete_doc_if_exists(
        "Company",
        {"abbr": "CTC", "company_name": "Compliance Test Company"},
        force=1,
    )
    company = frappe.new_doc("Company")

    company.company_name = "Compliance Test Company"
    company.abbr = "CTC"
    company.default_currency = "USD"
    company.country = "Kenya"
    company.tax_id = "A123456789Z"

    company.save()

    frappe.delete_doc_if_exists(
        "Company",
        {"abbr": "CTC2", "company_name": "Compliance Test Company 2"},
        force=1,
    )
    company = frappe.new_doc("Company")

    company.company_name = "Compliance Test Company 2"
    company.abbr = "CTC2"
    company.default_currency = "USD"
    company.country = "Kenya"
    company.tax_id = "A1234567890Z"

    company.save()


def create_test_branch(branch_name: str | None):
    branch = frappe.new_doc("Branch")

    branch.branch = branch_name or "100"
    branch.custom_branch_code = branch_name or "100"

    branch.save()


class TestNavariKRAeTimsSettings(FrappeTestCase):
    """Test Cases"""

    def __init__(self, methodName: str = "runTest") -> None:
        # Test Flags
        self.delete_hq_branch = False
        self.delete_branch_acct_dim = False

        super().__init__(methodName)

    def setUp(self) -> None:
        create_test_company()
        create_test_branch(None)
        create_test_branch("0")
        create_test_branch("failing test branch")

        # Delete branch 00 iff it was created in the test
        if not frappe.db.exists("Branch", {"custom_branch_code": "00"}):
            create_test_branch("00")
            self.delete_hq_branch = True

        if not frappe.db.exists("Accounting Dimension", "Branch", cache=False):
            self.delete_branch_acct_dim = True

        # Patch before_insert hook
        self.patcher = patch.object(
            NavariKRAeTimsSettings, "before_insert", new=mock_before_insert
        )
        # Start patch
        self.mock_method = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def tearDown(self) -> None:
        delete_doc(
            "Company",
            frappe.get_value(
                "Company",
                {"abbr": "CTC", "company_name": "Compliance Test Company"},
            ),
            force=1,
            ignore_permissions=True,
        )
        delete_doc(
            "Company",
            frappe.get_value(
                "Company",
                {"abbr": "CTC2", "company_name": "Compliance Test Company 2"},
            ),
            force=1,
            ignore_permissions=True,
        )
        delete_doc("Branch", "100")
        delete_doc("Branch", "0")
        delete_doc("Branch", "failing test branch")

        if self.delete_hq_branch:
            delete_doc("Branch", "00")

        if self.delete_branch_acct_dim:
            delete_doc("Accounting Dimension", "Branch")

        # I had to raw-dog SQL as delete_doc() wasn't working.
        # frappe.db.delete() doesn't also seem to work
        frappe.db.sql(
            f"""
            DELETE FROM `tab{SETTINGS_DOCTYPE_NAME}` WHERE company like '%Compliance Test Company%'
            """,
            auto_commit=True,
        )

        frappe.db.commit()

    def test_invalid_branch_id(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

            new_setting.bhfid = "100"
            new_setting.company = "Compliance Test Company"
            new_setting.tin = "A123456789Z"
            new_setting.dvcsrlno = "123456"

            new_setting.save()

            new_setting.bhfid = "0"
            new_setting.save()

            new_setting.bhfid = "failing test branch"
            new_setting.save()

        self.assertIsNone(
            frappe.db.exists(
                SETTINGS_DOCTYPE_NAME,
                {"abbr": "CTC", "company_name": "Compliance Test Company"},
                cache=False,
            )
        )

    def test_large_device_serial_number(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

            new_setting.bhfid = "00"
            new_setting.company = "Compliance Test Company"
            new_setting.tin = "A123456789Z"
            new_setting.dvcsrlno = """
            0bd7d5dacd2eadf8c1be64692ea461e648b0a0f359c4c4c5709033ee444821c5e6310dbf3f584fbcfa5e8837f1cd9e378583b929e21cb2a102f8c433a5000858348d8c292e25fe5a5b6ac8ff59bd78dd9e7dba3adce90b176ec19678aeece25ca1e13b02eb
            """

            new_setting.save()

    def test_invalid_kra_pin(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

            new_setting.bhfid = "00"
            new_setting.company = "Compliance Test Company 2"
            new_setting.dvcsrlno = "123456"

            new_setting.save()

    def test_mutually_exclusive_is_active_toggle(self) -> None:
        new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

        new_setting.bhfid = "00"
        new_setting.is_active = 1
        new_setting.company = "Compliance Test Company"
        new_setting.dvcsrlno = "123456"

        new_setting.save()

        new_setting_2 = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

        new_setting_2.bhfid = "00"
        new_setting_2.is_active = 1
        new_setting_2.company = "Compliance Test Company"
        new_setting_2.dvcsrlno = "54321"

        new_setting_2.save()

        all_active_envs = frappe.get_all(
            SETTINGS_DOCTYPE_NAME,
            {"company": "Compliance Test Company", "is_active": 1},
        )

        self.assertEqual(len(all_active_envs), 1)

    def test_incorrect_cron_formats(self) -> None:
        with self.assertRaises(frappe.ValidationError):
            new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

            new_setting.bhfid = "00"
            new_setting.is_active = 1
            new_setting.company = "Compliance Test Company"
            new_setting.dvcsrlno = "123456"
            new_setting.sales_information_submission = "Cron"
            new_setting.sales_info_cron_format = "* * * * * *"
            new_setting.stock_information_submission = "Cron"
            new_setting.stock_info_cron_format = "30 24 * * *"
            new_setting.stock_information_submission = "Cron"
            new_setting.purchase_info_cron_format = "* * * 13 5L"

            new_setting.save()

    def test_update_scheduled_job_through_settings(self) -> None:
        new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

        new_setting.bhfid = "00"
        new_setting.is_active = 1
        new_setting.company = "Compliance Test Company"
        new_setting.dvcsrlno = "123456"
        new_setting.sales_information_submission = "Cron"
        new_setting.sales_info_cron_format = "* * * * *"

        new_setting.save()

        task = send_sales_invoices_information.__name__

        scheduled_task: Document = frappe.get_doc(
            "Scheduled Job Type",
            {"method": ["like", f"%{task}%"]},
            ["name", "method", "frequency"],
            for_update=True,
        )

        self.assertEqual(scheduled_task.frequency, "Cron")
        self.assertEqual(scheduled_task.cron_format, "* * * * *")

    @patch.object(NavariKRAeTimsSettings, "before_insert", new=mock_before_insert_2)
    def test_auto_creation_of_acct_dimension(self) -> None:
        new_setting = frappe.new_doc(SETTINGS_DOCTYPE_NAME)

        new_setting.bhfid = "00"
        new_setting.is_active = 1
        new_setting.company = "Compliance Test Company"
        new_setting.dvcsrlno = "123456"
        new_setting.sales_information_submission = "Cron"
        new_setting.sales_info_cron_format = "* * * * *"
        new_setting.autocreate_branch_dimension = 1

        new_setting.save()

        self.assertTrue(frappe.db.exists("Accounting Dimension", "Branch", cache=False))
 