from .kenya_compliance.doctype.doctype_names_mapping import (
    COUNTRIES_DOCTYPE_NAME,
    IMPORTED_ITEMS_STATUS_DOCTYPE_NAME,
    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
    PACKAGING_UNIT_DOCTYPE_NAME,
    PAYMENT_TYPE_DOCTYPE_NAME,
    PRODUCT_TYPE_DOCTYPE_NAME,
    PURCHASE_RECEIPT_DOCTYPE_NAME,
    ROUTES_TABLE_DOCTYPE_NAME,
    STOCK_MOVEMENT_TYPE_DOCTYPE_NAME,
    TAXATION_TYPE_DOCTYPE_NAME,
    TRANSACTION_PROGRESS_DOCTYPE_NAME,
    TRANSACTION_TYPE_DOCTYPE_NAME,
    UNIT_OF_QUANTITY_DOCTYPE_NAME,
)

app_name = "kenya_compliance"
app_title = "Navari KRA eTIMS Integration"
app_publisher = "Navari Ltd"
app_description = (
    "KRA eTIMS Online Sales Control Unit (OSCU) Integration with ERPNext by Navari Ltd"
)
app_email = "solutions@navari.co.ke"
app_license = "GNU Affero General Public License v3.0"
required_apps = ["frappe/erpnext"]


# Fixtures
# --------
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "dt",
                "in",
                (
                    "Item",
                    "Sales Invoice",
                    "Sales Invoice Item",
                    "Purchase Invoice",
                    "Purchase Invoice Item",
                    "Customer",
                    "Customer Group",
                    "Stock Ledger Entry",
                    "BOM",
                    "Warehouse",
                    "Item Tax Template",
                    "Branch",
                    "Supplier",
                ),
            ],
            ["is_system_generated", "=", 0],
        ],
    },
    {"dt": TRANSACTION_TYPE_DOCTYPE_NAME},
    {"dt": PURCHASE_RECEIPT_DOCTYPE_NAME},
    {"dt": UNIT_OF_QUANTITY_DOCTYPE_NAME},
    {"dt": IMPORTED_ITEMS_STATUS_DOCTYPE_NAME},
    {"dt": ROUTES_TABLE_DOCTYPE_NAME},
    {"dt": COUNTRIES_DOCTYPE_NAME},
    {"dt": ITEM_CLASSIFICATIONS_DOCTYPE_NAME},
    {
        "dt": TAXATION_TYPE_DOCTYPE_NAME,
        "filters": [["name", "in", ("A", "B", "C", "D", "E")]],
    },
    {
        "dt": PRODUCT_TYPE_DOCTYPE_NAME,
        "filters": [["name", "in", (1, 2, 3)]],
    },
    {"dt": PACKAGING_UNIT_DOCTYPE_NAME},
    {"dt": STOCK_MOVEMENT_TYPE_DOCTYPE_NAME},
    {
        "dt": PAYMENT_TYPE_DOCTYPE_NAME,
        "filters": [
            [
                "name",
                "in",
                (
                    "CASH",
                    "CREDIT",
                    "CASH/CREDIT",
                    "BANK CHECK",
                    "DEBIT&CREDIT CARD",
                    "MOBILE MONEY",
                    "OTHER",
                ),
            ]
        ],
    },
    {
        "dt": TRANSACTION_PROGRESS_DOCTYPE_NAME,
        "filters": [
            [
                "name",
                "in",
                (
                    "Wait for Approval",
                    "Approved",
                    "Cancel Requested",
                    "Canceled",
                    "Credit Note Generated",
                    "Transferred",
                ),
            ]
        ],
    },
]
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kenya_compliance/css/kenya_compliance.css"
# app_include_js = "/assets/kenya_compliance/js/kenya_compliance.js"

# include js, css files in header of web template
# web_include_css = "/assets/kenya_compliance/css/kenya_compliance.css"
# web_include_js = "/assets/kenya_compliance/js/kenya_compliance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kenya_compliance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice": "kenya_compliance/overrides/client/sales_invoice.js",
    "Purchase Invoice": "kenya_compliance/overrides/client/purchase_invoice.js",
    "Customer": "kenya_compliance/overrides/client/customer.js",
    "Item": "kenya_compliance/overrides/client/items.js",
    "BOM": "kenya_compliance/overrides/client/bom.js",
    "Branch": "kenya_compliance/overrides/client/branch.js",
}

doctype_list_js = {
    "Item": "kenya_compliance/overrides/client/items_list.js",
    "Sales Invoice": "kenya_compliance/overrides/client/sales_invoice_list.js",
    "Branch": "kenya_compliance/overrides/client/branch_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "kenya_compliance/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "kenya_compliance.utils.jinja_methods",
# 	"filters": "kenya_compliance.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kenya_compliance.install.before_install"
# after_install = "kenya_compliance.kenya_compliance.setup.after_install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kenya_compliance.uninstall.before_uninstall"
# after_uninstall = (
#     "kenya_compliance.kenya_compliance.setup.after_uninstall.after_uninstall"
# )

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kenya_compliance.utils.before_app_install"
# after_app_install = "kenya_compliance.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kenya_compliance.utils.before_app_uninstall"
# after_app_uninstall = "kenya_compliance.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kenya_compliance.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    # 	"*": {
    # 		"on_update": "method",
    # 		"on_cancel": "method",
    # 		"on_trash": "method"
    # 	}
    "Sales Invoice": {
        "before_save":[
            "kenya_compliance.kenya_compliance.utils.before_save_"
        ],
        "on_submit": [
            "kenya_compliance.kenya_compliance.overrides.server.sales_invoice.on_submit"
        ],
        "validate": [
            "kenya_compliance.kenya_compliance.overrides.server.shared_overrides.validate"
        ],
        "before_cancel":[
            "kenya_compliance.kenya_compliance.overrides.server.sales_invoice.before_cancel"
        ],
    },
    "Purchase Invoice": {
        "before_save":[
            "kenya_compliance.kenya_compliance.utils.before_save_"
        ],
        "on_submit": [
            "kenya_compliance.kenya_compliance.overrides.server.purchase_invoice.on_submit"
        ],
        "validate": [
            "kenya_compliance.kenya_compliance.overrides.server.purchase_invoice.validate"
        ],
        "before_cancel":[
            "kenya_compliance.kenya_compliance.overrides.server.sales_invoice.before_cancel"
        ],
    },
    "Item": {
        "validate": [
            "kenya_compliance.kenya_compliance.overrides.server.item.validate"
        ],
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "all": [
        "kenya_compliance.kenya_compliance.background_tasks.tasks.send_stock_information",
        "kenya_compliance.kenya_compliance.background_tasks.tasks.send_item_inventory_information",
    ],
    # 	"daily": [
    # 		"kenya_compliance.tasks.daily"
    # 	],
    "hourly": [
        "kenya_compliance.kenya_compliance.background_tasks.tasks.send_sales_invoices_information",
        "kenya_compliance.kenya_compliance.background_tasks.tasks.send_purchase_information",
        "kenya_compliance.kenya_compliance.background_tasks.tasks.refresh_notices",
    ],
    # 	"weekly": [
    # 		"kenya_compliance.tasks.weekly"
    # 	],
    "monthly": [
        "kenya_compliance.kenya_compliance.background_tasks.tasks.refresh_code_lists",
        "kenya_compliance.kenya_compliance.background_tasks.tasks.get_item_classification_codes",
    ],
}

# Testing
# -------

# before_tests = "kenya_compliance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "kenya_compliance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kenya_compliance.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["kenya_compliance.utils.before_request"]
# after_request = ["kenya_compliance.utils.after_request"]

# Job Events
# ----------
# before_job = ["kenya_compliance.utils.before_job"]
# after_job = ["kenya_compliance.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kenya_compliance.auth.validate"
# ]
