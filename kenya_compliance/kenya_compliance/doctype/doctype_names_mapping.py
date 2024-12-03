"""Maps doctype names defined and used in the app to variable names"""

from typing import Final

# Doctypes
SETTINGS_DOCTYPE_NAME: Final[str] = "Navari Slade360 eTims Settings"
ROUTES_TABLE_DOCTYPE_NAME: Final[str] = "Navari eTims Routes"
ROUTES_TABLE_CHILD_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Route Table Item"
ITEM_CLASSIFICATIONS_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Item Classification"
TAXATION_TYPE_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Taxation Type"
PAYMENT_TYPE_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Payment Type"
TRANSACTION_PROGRESS_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Transaction Progress"
PACKAGING_UNIT_DOCTYPE_NAME: Final[str] = "Navari eTims Packaging Unit"
UNIT_OF_QUANTITY_DOCTYPE_NAME: Final[str] = "Navari eTims Unit of Quantity"
ENVIRONMENT_SPECIFICATION_DOCTYPE_NAME: Final[str] = (
    "Navari KRA eTims Environment Identifier"
)
INTEGRATION_LOGS_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Integration Log"
STOCK_MOVEMENT_TYPE_DOCTYPE_NAME: Final[str] = "Navari eTims Stock Movement Type"
PRODUCT_TYPE_DOCTYPE_NAME: Final[str] = "Navari eTims Product Type"
COUNTRIES_DOCTYPE_NAME: Final[str] = "Navari eTims Country"
IMPORTED_ITEMS_STATUS_DOCTYPE_NAME: Final[str] = "Navari eTims Import Item Status"
PURCHASE_RECEIPT_DOCTYPE_NAME: Final[str] = "Navari eTims Purchase Receipt Type"
TRANSACTION_TYPE_DOCTYPE_NAME: Final[str] = "Navari eTims Transaction Type"
REGISTERED_PURCHASES_DOCTYPE_NAME: Final[str] = "Navari eTims Registered Purchases"
REGISTERED_PURCHASES_DOCTYPE_NAME_ITEM: Final[str] = (
    "Navari eTims Registered Purchases Items"
)
NOTICES_DOCTYPE_NAME: Final[str] = "Navari KRA eTims Notices"
USER_DOCTYPE_NAME: Final[str] = "Navari eTims User"
REGISTERED_STOCK_MOVEMENTS_DOCTYPE_NAME: Final[str] = (
    "Navari eTims Registered Stock Movement"
)
REGISTERED_STOCK_MOVEMENTS_ITEM_DOCTYPE_NAME: Final[str] = (
    "Navari eTims Registered Stock Movement Item"
)
REGISTERED_IMPORTED_ITEM_DOCTYPE_NAME: Final[str] = (
    "Navari eTims Registered Imported Item"
)

# Global Variables
SANDBOX_SERVER_URL: Final[str] = "https://etims-api-sbx.kra.go.ke/etims-api"
PRODUCTION_SERVER_URL: Final[str] = "https://etims-api.kra.go.ke/etims-api"
