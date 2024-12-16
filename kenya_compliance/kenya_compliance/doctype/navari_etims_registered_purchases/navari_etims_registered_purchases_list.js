const doctypeName = "Navari eTims Registered Purchases";

frappe.listview_settings[doctypeName] = {
  onload: function (listview) {
    const companyName = frappe.boot.sysdefaults.company;

    listview.page.add_inner_button(
      __("Get Raised Purchases"),
      function (listview) {
        frappe.call({
          method:
            "kenya_compliance.kenya_compliance.apis.apis.perform_purchases_search_all_branches",
          args: {
            request_data: {
              company_name: companyName,
            },
          },
          callback: (response) => {},
          error: (error) => {
            // Error Handling is Defered to the Server
          },
        });
      }
    );
  },
};
