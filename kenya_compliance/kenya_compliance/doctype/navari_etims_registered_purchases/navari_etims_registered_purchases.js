// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt
const doctypeName = 'Navari eTims Registered Purchases';

frappe.ui.form.on(doctypeName, {
  refresh: function (frm) {
    const companyName = frappe.boot.sysdefaults.company;

    if (!frm.is_new()) {
      frm.add_custom_button(
        __('Create Supplier'),
        function () {
          frappe.call({
            method:
              'kenya_compliance.kenya_compliance.apis.apis.create_supplier_from_fetched_registered_purchases',
            args: {
              request_data: {
                name: frm.doc.name,
                company_name: companyName,
                supplier_name: frm.doc.supplier_name,
                supplier_pin: frm.doc.supplier_pin,
                supplier_branch_id: frm.doc.supplier_branch_id,
              },
            },
            callback: (response) => {},
            error: (error) => {
              // Error Handling is Defered to the Server
            },
          });
        },
        __('eTims Actions'),
      );
      // frm.add_custom_button(
      //   __('Create Items'),
      //   function () {
      //     frappe.call({
      //       method:
      //         'kenya_compliance.kenya_compliance.apis.apis.create_items_from_fetched_registered_purchases',
      //       args: {
      //         request_data: {
      //           name: frm.doc.name,
      //           company_name: companyName,
      //           items: frm.doc.items,
      //         },
      //       },
      //       callback: (response) => {},
      //       error: (error) => {
      //         // Error Handling is Defered to the Server
      //       },
      //     });
      //   },
      //   __('eTims Actions'),
      // );
  // Check for unmapped items before adding the "Create Items" button
  frappe.call({
    method: 'kenya_compliance.kenya_compliance.doctype.navari_etims_registered_purchases.navari_etims_registered_purchases.validate_item_mapped_and_registered',
    args: {
      items: frm.doc.items,
    },
    callback: (response) => {
      if (response.message === false) {
        frm.add_custom_button(
          __('Create Items'),
          function () {
            frappe.call({
              method:
                'kenya_compliance.kenya_compliance.apis.apis.create_items_from_fetched_registered_purchases',
              args: {
                request_data: {
                  name: frm.doc.name,
                  company_name: companyName,
                  items: frm.doc.items,
                },
              },
              callback: (response) => {},
              error: (error) => {
              },
            });
          },
          __('eTims Actions'),
        );
      }
    },
    error: (error) => {
      frappe.msgprint(__('Failed to validate items.'));
    },
  });

      frm.add_custom_button(
        __('Create Purchase Invoice'),
        function () {
          frappe.call({
            method:
              'kenya_compliance.kenya_compliance.apis.apis.create_purchase_invoice_from_request',
            args: {
              request_data: {
                name: frm.doc.name,
                company_name: companyName,
                supplier_name: frm.doc.supplier_name,
                supplier_pin: frm.doc.supplier_pin,
                supplier_branch_id: frm.doc.supplier_branch_id,
                supplier_invoice_no: frm.doc.supplier_invoice_number,
                supplier_invoice_date: frm.doc.sales_date,
                items: frm.doc.items,
              },
            },
            callback: (response) => {},
            error: (error) => {
              // Error Handling is Defered to the Server
            },
          });
        },
        __('eTims Actions'),
      );
      // frm.add_custom_button(
      //   __("Create Purchase Receipt"),
      //   function () {
      //     frappe.call({
      //       method: null,
      //       args: {
      //         request_data: {
      //           name: frm.doc.name,
      //           company_name: companyName,
      //           supplier_name: frm.doc.supplier_name,
      //           supplier_pin: frm.doc.supplier_pin,
      //           items: frm.doc.items,
      //         },
      //       },
      //       callback: (response) => {},
      //       error: (error) => {
      //         // Error Handling is Defered to the Server
      //       },
      //     });
      //   },
      //   __("eTims Actions")
      // );
    }
  },
});
