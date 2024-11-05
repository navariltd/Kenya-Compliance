import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from .shared_overrides import generic_invoices_on_submit_override

class TestGenericInvoicesOnSubmit(FrappeTestCase):
    """Test Cases for Generic Invoices On Submit"""

    def setUp(self) -> None:
        pass

    @patch('frappe.enqueue')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.build_headers')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.get_server_url')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.get_route_path')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.build_invoice_payload')
    def test_generic_invoices_on_submit_sales_invoice(
        self, mock_build_invoice_payload, mock_get_route_path, mock_get_server_url, mock_build_headers, mock_enqueue
    ):
        """Test case for submitting a Sales Invoice."""
        
        # Mocking the expected outputs
        mock_build_headers.return_value = {'Authorization': 'Bearer token'}
        mock_get_server_url.return_value = 'https://server.url'
        mock_get_route_path.return_value = ('/api/route', 'last_date')
        mock_build_invoice_payload.return_value = {'invcNo': 'INV-001'}

        # Creating a mock document object
        doc = MagicMock()
        doc.company = "Test Company"
        doc.branch = "Main Branch"
        doc.is_return = False
        doc.name = "INV-001"

        # Call the function being tested
        generic_invoices_on_submit_override(doc, "Sales Invoice")

        # Validating the behavior
        mock_build_headers.assert_called_with('Test Company', 'Main Branch')
        mock_get_server_url.assert_called_with('Test Company', 'Main Branch')
        mock_get_route_path.assert_called_with('TrnsSalesSaveWrReq')
        mock_build_invoice_payload.assert_called_with(doc, "S", "Test Company")
        mock_enqueue.assert_called_once()

    @patch('frappe.enqueue')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.build_headers')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.get_server_url')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.get_route_path')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.build_invoice_payload')
    def test_generic_invoices_on_submit_pos_invoice(
        self, mock_build_invoice_payload, mock_get_route_path, mock_get_server_url, mock_build_headers, mock_enqueue
    ):
        """Test case for submitting a POS Invoice."""
        
        # Mocking the expected outputs
        mock_build_headers.return_value = {'Authorization': 'Bearer token'}
        mock_get_server_url.return_value = 'https://server.url'
        mock_get_route_path.return_value = ('/api/route', 'last_date')
        mock_build_invoice_payload.return_value = {'invcNo': 'POS-001'}

        # Creating a mock document object
        doc = MagicMock()
        doc.company = "Test Company"
        doc.branch = "Main Branch"
        doc.is_return = True
        doc.name = "POS-001"

        # Call the function being tested
        generic_invoices_on_submit_override(doc, "POS Invoice")

        # Validating the behavior
        mock_build_headers.assert_called_with('Test Company', 'Main Branch')
        mock_get_server_url.assert_called_with('Test Company', 'Main Branch')
        mock_get_route_path.assert_called_with('TrnsSalesSaveWrReq')
        mock_build_invoice_payload.assert_called_with(doc, "C", "Test Company")
        mock_enqueue.assert_called_once()

    @patch('frappe.enqueue')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.build_headers')
    @patch('kenya_compliance.kenya_compliance.overrides.server.shared_overrides.get_server_url')
    def test_generic_invoices_on_submit_missing_server_url(
        self, mock_get_server_url, mock_build_headers, mock_enqueue
    ):
        """Test case when the server URL is missing."""
        
        # Mocking the expected outputs
        mock_build_headers.return_value = {'Authorization': 'Bearer token'}
        mock_get_server_url.return_value = None  # No server URL
        
        # Creating a mock document object
        doc = MagicMock()
        doc.company = "Test Company"
        doc.branch = "Main Branch"
        doc.is_return = False
        doc.name = "INV-001"

        # Call the function being tested
        generic_invoices_on_submit_override(doc, "Sales Invoice")

        # Validating the behavior: enqueue should not be called since server URL is missing
        mock_enqueue.assert_not_called()

    def tearDown(self) -> None:
        """Clean up after each test."""
        super().tearDown()  
