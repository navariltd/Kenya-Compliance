// const doctypeName = "Navari eTims Registered Stock Movement";

// frappe.listview_settings[doctypeName] = {
//   onload: function (listview) {
//     const companyName = frappe.boot.sysdefaults.company;

//     listview.page.add_inner_button(
//       __("Get Stock Movements"),
//       function (listview) {
//         frappe.call({
//           method:
//             "kenya_compliance.kenya_compliance.apis.apis.perform_stock_movement_search",
//           args: {
//             request_data: {
//               company_name: companyName,
//               branch_id: "",
//             },
//           },
//           callback: (response) => {},
//           error: (error) => {
//             // Error Handling is Defered to the Server
//           },
//         });
//       },
//     );
//   },
// };
const doctypeName = "Navari eTims Registered Stock Movement";

frappe.listview_settings[doctypeName] = {
  onload: function (listview) {
    const companyName = frappe.boot.sysdefaults.company;

    listview.page.add_inner_button(
      __("Get Stock Movements"),
      function () {
        // Create a dialog to select a branch
        const branchDialog = new frappe.ui.Dialog({
          title: __("Select Branch"),
          fields: [
            {
              label: __("Branch"),
              fieldname: "branch_id",
              fieldtype: "Link",
              options: "Branch",
              reqd: true,
            },
          ],
          primary_action_label: __("Submit"),
          primary_action: function (data) {
            branchDialog.hide();

            // Call the server method with the selected branch
            frappe.call({
              method:
                "kenya_compliance.kenya_compliance.apis.apis.perform_stock_movement_search",
              args: {
                request_data: {
                  company_name: companyName,
                  branch_id: data.branch_id, 
                },
              },
              callback: (response) => {
                frappe.msgprint(__("Stock movements retrieved successfully."));
              },
              error: (error) => {
                frappe.msgprint(__("An error occurred while fetching stock movements."));
              },
            });
          },
        });

        // Show the dialog
        branchDialog.show();
      },
    );
  },
};

