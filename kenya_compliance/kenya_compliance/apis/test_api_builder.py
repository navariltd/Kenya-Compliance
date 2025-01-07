import asyncio
from datetime import datetime
from functools import partial
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import frappe
from frappe.model.delete_doc import delete_doc
from frappe.tests.utils import FrappeTestCase

from .api_builder import EndpointsBuilder


def patched_update_request_date(*args, **kwargs) -> Any:
    return lambda *args, **kwargs: (args, kwargs)


class TestApis(FrappeTestCase):
    """Test Cases"""

    @patch(
        "kenya_compliance.kenya_compliance.apis.api_builder.update_last_request_date",
        new_callable=patched_update_request_date,
    )
    @patch(
        "kenya_compliance.kenya_compliance.apis.api_builder.make_post_request",
        new_callable=AsyncMock,
    )
    def test_make_post_request_success(
        self, mock_make_post_request: MagicMock, mock_update_request_date: MagicMock
    ) -> None:
        mock_response = {
            "resultCd": "000",
            "resultMsg": "Success",
            "resultDt": "20240101000000",
        }
        mock_make_post_request.return_value = mock_response

        url = "https://test.com/"
        data = {"test_data": "Test Data"}
        headers = {"Content-Type": "application/json"}

        e = EndpointsBuilder()
        e.url = url
        e.headers = headers
        e.payload = data
        e.success_callback = lambda *args, **kwargs: None
        e.error_callback = lambda *args, **kwargs: None

        e.make_remote_call()

        frappe.db.commit()

        record = frappe.get_all(
            "Integration Request",
            {
                "is_remote_request": 1,
                "url": url,
                "request_headers": headers,
                "data": data,
            },
            ["*"],
            limit=1,
        )

        self.assertIsNotNone(record)
        self.assertEqual(record[0].output, mock_response["resultMsg"])

    @patch(
        "kenya_compliance.kenya_compliance.apis.api_builder.update_last_request_date",
        new_callable=patched_update_request_date,
    )
    @patch(
        "kenya_compliance.kenya_compliance.apis.api_builder.make_post_request",
        new_callable=AsyncMock,
    )
    def test_make_post_request_failed(
        self, mock_make_post_request: MagicMock, mock_update_request_date: MagicMock
    ) -> None:
        mock_response = {
            "resultCd": "001",
            "resultMsg": "Errored",
            "resultDt": "20240101000000",
        }
        mock_make_post_request.return_value = mock_response

        url = "https://test.com/"
        data = {"test_data": "Test Data"}
        headers = {"Content-Type": "application/json"}

        e = EndpointsBuilder()
        e.url = url
        e.headers = headers
        e.payload = data
        e.success_callback = lambda *args, **kwargs: None
        e.error_callback = lambda *args, **kwargs: None

        e.make_remote_call()

        frappe.db.commit()

        record = frappe.get_all(
            "Integration Request",
            {
                "is_remote_request": 1,
                "url": url,
                "request_headers": headers,
                "data": data,
            },
            ["*"],
            limit=1,
        )

        self.assertIsNotNone(record)
        self.assertEqual(record[0].error, mock_response["resultMsg"])


