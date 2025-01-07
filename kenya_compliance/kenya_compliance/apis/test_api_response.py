import frappe
from frappe.tests.utils import FrappeTestCase

from .apis import (
    purchase_search_on_success,
)
from .remote_response_status_handlers import (
     check_duplicate_registered_purchase,
    create_and_link_purchase_item,
    create_purchase_from_search_details
)

from ..doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
    NOTICES_DOCTYPE_NAME,
    PACKAGING_UNIT_DOCTYPE_NAME,
    REGISTERED_IMPORTED_ITEM_DOCTYPE_NAME,
    REGISTERED_PURCHASES_DOCTYPE_NAME,
    REGISTERED_PURCHASES_DOCTYPE_NAME_ITEM,
    REGISTERED_STOCK_MOVEMENTS_DOCTYPE_NAME,
    UNIT_OF_QUANTITY_DOCTYPE_NAME,
    USER_DOCTYPE_NAME,
)
class TestPurchaseSearch(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Any additional setup steps go here, e.g., creating custom doctypes or fixtures.

    def tearDown(self):
        super().tearDown()
        # Clean up test data
        frappe.db.delete(REGISTERED_PURCHASES_DOCTYPE_NAME)
        frappe.db.delete(REGISTERED_PURCHASES_DOCTYPE_NAME_ITEM,)

    def sample_response(self):
        return {
            "resultCd": "000",
            "resultMsg": "It is succeeded",
            "resultDt": "20200226195420",
            "data": {
                "saleList": [
                    {
                        "spplrTin": "A123456789Z",
                        "spplrNm": "Taxpayer1111",
                        "spplrBhfId": "00",
                        "spplrInvcNo": 2,
                        "rcptTyCd": "S",
                        "pmtTyCd": "01",
                        "cfmDt": "2020-01-27 21:03:00",
                        "salesDt": "20200127",
                        "stockRlsDt": "2020-01-27 21:03:00",
                        "totItemCnt": 2,
                        "totTaxblAmt": 10500,
                        "totTaxAmt": 1602,
                        "totAmt": 10500,
                        "itemList": [
                            {
                                "itemSeq": 1,
                                "itemCd": "KE1NTXU0000001",
                                "itemNm": "test item 1",
                                "qty": 2,
                                "prc": 3500,
                                "taxblAmt": 7000,
                                "taxAmt": 1068,
                                "totAmt": 7000,
                            },
                            {
                                "itemSeq": 2,
                                "itemCd": "KE1NTXU0000002",
                                "itemNm": "test item 2",
                                "qty": 1,
                                "prc": 3500,
                                "taxblAmt": 3500,
                                "taxAmt": 534,
                                "totAmt": 3500,
                            },
                        ],
                    }
                ]
            },
        }

    def test_purchase_search_on_success(self):
        response = self.sample_response()
        purchase_search_on_success(response)

        sales_list = response["data"]["saleList"]
        for sale in sales_list:
            unique_id = f"{sale['spplrTin']}-{sale['spplrInvcNo']}"
            self.assertTrue(frappe.db.exists(REGISTERED_PURCHASES_DOCTYPE_NAME, unique_id))

            doc = frappe.get_doc(REGISTERED_PURCHASES_DOCTYPE_NAME, unique_id)
            self.assertEqual(len(doc.items), len(sale["itemList"]))

            for item in sale["itemList"]:
                item_exists = any(child.item_code == item["itemCd"] for child in doc.items)
                self.assertTrue(item_exists)

    def test_check_duplicate_registered_purchase(self):
        response = self.sample_response()
        sale = response["data"]["saleList"][0]
        unique_id = f"{sale['spplrTin']}-{sale['spplrInvcNo']}"

        # Create a duplicate record manually
        doc = frappe.new_doc(REGISTERED_PURCHASES_DOCTYPE_NAME)
        doc.name = unique_id
        doc.insert()
    
        duplicate_id = check_duplicate_registered_purchase(sale)
        self.assertEqual(duplicate_id, unique_id)

    def test_create_purchase_from_search_details(self):
        response = self.sample_response()
        sale = response["data"]["saleList"][0]

        doc_name = create_purchase_from_search_details(sale)

        self.assertTrue(frappe.db.exists(REGISTERED_PURCHASES_DOCTYPE_NAME, doc_name))

        doc = frappe.get_doc(REGISTERED_PURCHASES_DOCTYPE_NAME, doc_name)
        self.assertEqual(doc.supplier_name, sale["spplrNm"])
        self.assertEqual(doc.total_amount, sale["totAmt"])

    def test_create_and_link_purchase_item(self):
        response = self.sample_response()
        sale = response["data"]["saleList"][0]
        sale_doc_name = create_purchase_from_search_details(sale)
        item = sale["itemList"][0]

        create_and_link_purchase_item(item, sale_doc_name)

        doc = frappe.get_doc(REGISTERED_PURCHASES_DOCTYPE_NAME, sale_doc_name)
        linked_item = next(
            (child for child in doc.items if child.item_code == item["itemCd"]), None
        )

        self.assertIsNotNone(linked_item)
        self.assertEqual(linked_item.item_name, item["itemNm"])
