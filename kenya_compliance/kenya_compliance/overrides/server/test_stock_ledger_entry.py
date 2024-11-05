import frappe
from frappe.tests.utils import FrappeTestCase
from .stock_ledger_entry import (
    on_update,
    get_stock_entry_movement_items_details,
    get_stock_recon_movement_items_details,
    get_purchase_docs_items_details,
    get_notes_docs_items_details,
    get_warehouse_branch_id
)
from hashlib import sha256

class TestStockLedgerEntry(FrappeTestCase):

    def setUp(self) -> None:
        """
        Setup method to create necessary test data before running each test.
        """
        # Define test data
        self.company_name = "Test Company"
        self.customer_name = "Test Customer"
        self.supplier_name = "Test Supplier"
        self.item_code = "TEST-ITEM"
        self.warehouse_name = "Test Warehouse"
        self.from_currency = "KES"
        self.to_currency = "USD"

        # Define document types and their filters for cleanup
        self.doc_types = [
            ("Stock Entry", {"company": self.company_name}),
            ("Stock Reconciliation", {"company": self.company_name}),
            ("Purchase Invoice", {"company": self.company_name}),
            ("Delivery Note", {"company": self.company_name}),
            ("Currency Exchange", {"from_currency": self.from_currency, "to_currency": self.to_currency}),
            ("Item", {"item_code": self.item_code}),
            ("Warehouse", {"warehouse_name": self.warehouse_name}),
            ("Supplier", {"supplier_name": self.supplier_name}),
            ("Customer", {"customer_name": self.customer_name}),
        ]

        # Cleanup existing records if they exist
        for doc_type, filters in self.doc_types:
            for doc in frappe.get_all(doc_type, filters=filters):
                frappe.delete_doc(doc_type, doc.name)
        frappe.delete_doc(
            "Company",
            frappe.get_value(
                "Company",
                {"abbr": "TTC", "company_name": "Test Company"},
            ),
            force=1,
            ignore_permissions=True,
        )
        frappe.delete_doc("Branch", "00", force=1, ignore_permissions=True)
                
        # Create Test Company and branch
        self.company, self.branch_doc = create_test_company()

        # Create test records
        self.customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": self.customer_name
        }).insert()

        self.supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": self.supplier_name
        }).insert()

        self.warehouse = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": self.warehouse_name,
            "company": self.company.name
        }).insert()

        # Fetch existing records for item setup
        self.custom_product_type = frappe.get_all("Navari eTims Product Type", limit=1)[0]
        self.packaging_unit_doc = frappe.get_all("Navari eTims Packaging Unit", limit=1)[0]
        self.unit_of_quantity_doc = frappe.get_all("Navari eTims Unit of Quantity", limit=1)[0]
        self.custom_item_classification = frappe.get_all("Navari KRA eTims Item Classification", limit=1)[0]
        self.custom_etims_country_of_origin = frappe.get_all("Navari eTims Country", limit=1)[0]

        # Create or get a test item
        self.item = frappe.get_doc({
            "doctype": "Item",
            "item_code": self.item_code,
            "item_name": "Test Item",
            "item_group": "All Item Groups",
            "stock_uom": "Unit",
            "custom_product_type": self.custom_product_type.name,
            "custom_packaging_unit": self.packaging_unit_doc.name,
            "custom_unit_of_quantity": self.unit_of_quantity_doc.name,
            "custom_item_classification": self.custom_item_classification.name,
            "custom_etims_country_of_origin": self.custom_etims_country_of_origin.name,
            "default_warehouse": self.warehouse.name
        }).insert()
        
        # Create a test stock entry
        self.stock_entry = frappe.get_doc({
            'doctype': 'Stock Entry',
            'stock_entry_type': 'Material Receipt',
            'company': 'Test Company',
            'items': [{
                'item_code': self.item.item_code,
                'qty': 10,
                't_warehouse': self.warehouse.name 
            }]
        }).insert()

        # Add currency exchange rate
        self.currency_exchange_rate = frappe.get_doc({
            "doctype": "Currency Exchange",
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "exchange_rate": 0.007
        }).insert()

    def tearDown(self) -> None:
        """
        Cleanup method to remove test data after each test.
        """
        # Delete test documents
        frappe.delete_doc('Stock Entry', self.stock_entry.name)
        frappe.delete_doc('Item', self.item.name)
        frappe.delete_doc('Warehouse', self.warehouse.name)

    def test_get_warehouse_branch_id(self) -> None:
        # Set branch ID for warehouse
        frappe.db.set_value('Warehouse', self.warehouse.name, 'custom_branch', 'BR001')
        result = get_warehouse_branch_id(self.warehouse.name)
        self.assertEqual(result, 'BR001')

    def test_on_update_stock_entry(self) -> None:
        # Get the Stock Entry document before calling on_update
        doc_before = frappe.get_doc('Stock Entry', self.stock_entry.name)
        doc_before.voucher_type = "Stock Entry"
        doc_before.voucher_no = doc_before.name
        
        # Call the on_update method with the document
        on_update(doc_before)
        
        # Reload the document to reflect any updates made by the on_update function
        doc_after = frappe.get_doc('Stock Entry', self.stock_entry.name)
        
        # Assertions to verify expected updates or effects of on_update
        self.assertEqual(doc_after.modified_by, frappe.session.user, "Document should be modified by the current user")
        self.assertIsNotNone(doc_after.modified, "Modified time should be updated after on_update")
        
        # Check if a job for the stock entry exists in the job queue
        job_queue = frappe.get_all('RQ Job', filters={'job_name': sha256(f"{doc_before.name}{doc_before.creation}{doc_before.modified}".encode(), usedforsecurity=False).hexdigest()})
        self.assertGreater(len(job_queue), 0, "A job for the stock entry should be present in the job queue")

    def test_get_stock_entry_movement_items_details(self) -> None:
        records = [{
            'item_code': self.item.item_code,
            'qty': 10,
            'basic_rate': 100
        }]
        stock_movement_details = get_stock_entry_movement_items_details(records, [self.item])
        self.assertEqual(len(stock_movement_details), 1)
        self.assertEqual(stock_movement_details[0]['itemNm'], self.item.item_code)
        self.assertEqual(stock_movement_details[0]['prc'], 100)

    def test_get_stock_recon_movement_items_details(self) -> None:
        records = [{
            'item_code': self.item.item_code,
            'quantity_difference': 5,
            'valuation_rate': 50
        }]
        recon_movement_details = get_stock_recon_movement_items_details(records, [self.item])
        self.assertEqual(len(recon_movement_details), 1)
        self.assertEqual(recon_movement_details[0]['itemNm'], self.item.item_code)
        self.assertEqual(recon_movement_details[0]['qty'], 5)

    def test_get_purchase_docs_items_details(self) -> None:
        items = [{
            'item_code': self.item.item_code,
            'qty': 10,
            'valuation_rate': 100
        }]
        purchase_details = get_purchase_docs_items_details(items, [self.item])
        self.assertEqual(len(purchase_details), 1)
        self.assertEqual(purchase_details[0]['itemNm'], self.item.item_code)

    def test_get_notes_docs_items_details(self) -> None:
        items = [{
            'item_code': self.item.item_code,
            'qty': 10,
            'base_net_rate': 100
        }]
        notes_details = get_notes_docs_items_details(items, [self.item])
        self.assertEqual(len(notes_details), 1)
        self.assertEqual(notes_details[0]['itemNm'], self.item.item_code)
        self.assertEqual(notes_details[0]['prc'], 100)

def create_test_company():
    # Delete any existing test company with the same identifier
    existing_company = frappe.get_all("Company", filters={"abbr": "TTC", "company_name": "Test Company"})
    if existing_company:
        company_name = frappe.get_value("Company", {"abbr": "TTC", "company_name": "Test Company"})
        frappe.delete_doc("Company", company_name, force=1, ignore_permissions=True)

    # Create the test company
    company = frappe.get_doc({
        "doctype": "Company",
        "company_name": "Test Company",
        "abbr": "TTC",
        "default_currency": "USD",
        "country": "Kenya",
        "tax_id": "A123456787Z"
    })
    company.insert(ignore_permissions=True)

    # Create a test branch
    branch = frappe.get_doc({
        "doctype": "Branch",
        "branch": "00",
        "company": company.name,
        "abbr": "BRNT",
        "is_group": 0
    })
    branch.insert(ignore_permissions=True)

    return company, branch
