const doctypeName = 'Navari eTims Registered Imported Item';

frappe.ui.form.on(doctypeName, {
  refresh: function (frm) {
    const companyName = frappe.boot.sysdefaults.company;
    const item = [
      {
        item_classification_code: null,
        taxation_type_code: null,
        item_code: null,
        item_name: frm.doc.item_name,
        packaging_unit_code: frm.doc.packaging_unit_code,
        quantity_unit_code: frm.doc.quantity_unit_code,
        unit_price:
          parseFloat(frm.doc.invoice_foreign_currency_amount) /
          parseFloat(frm.doc.quantity).toFixed(2),
        quantity: frm.doc.quantity,
        imported_item: frm.doc.name,
        task_code: frm.doc.task_code,
      },
    ];

    if (!frm.is_new()) {
      frm.add_custom_button(
        __('Create Item'),
        function () {
          frappe.call({
            method:
              'kenya_compliance.kenya_compliance.apis.apis.create_items_from_fetched_registered_purchases',
            args: {
              request_data: {
                items: item,
              },
            },
            callback: (response) => {
              frappe.msgprint(
                'Item has been created. Please go to the created Item and provide required eTims Details.',
              );
            },
            error: (error) => {
              // Error Handling is Defered to the Server
            },
          });
        },
        __('eTims Actions'),
      );

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
                supplier_name: frm.doc.suppliers_name,
                supplier_pin: null,
                supplier_branch_id: null,
                supplier_currency: frm.doc.invoice_foreign_currency,
                supplier_nation: frm.doc.origin_nation_code,
              },
            },
            callback: (response) => {
              frappe.msgprint(
                'Supplier has been created. Please confirm the details captured.',
              );
            },
            error: (error) => {
              // Error Handling is Defered to the Server
            },
          });
        },
        __('eTims Actions'),
      );

      frappe.db.get_value(
        'Item',
        { custom_referenced_imported_item: frm.doc.name },
        ['custom_item_registered','name'],
        (response) => {
          if (parseInt(response.custom_item_registered) === 1) {
            frm.add_custom_button(
              __('Create Purchase Invoice'),
              function () {
                frappe.call({
                  method:
                    'kenya_compliance.kenya_compliance.apis.apis.create_purchase_invoice_from_request',
                  args: {
                    request_data: {
                      name: frm.doc.name,
                      supplier_invoice_no: null,
                      supplier_invoice_date: null,
                      supplier_name: frm.doc.suppliers_name,
                      supplier_branch_id: null,
                      exchange_rate: frm.doc.invoice_foreign_currency_rate,
                      currency: frm.doc.invoice_foreign_currency,
                      amount: frm.doc.invoice_foreign_currency_amount,
                      items: item,
                      task_code: frm.doc.task_code,
                    },
                  },
                  callback: (response) => {
                    frappe.msgprint(
                      'Purchase Invoice has been created. Please go to the created Invoice and provide required eTims Details.',
                    );
                  },
                  error: (error) => {
                    // Error Handling is Defered to the Server
                  },
                });
              },
              __('eTims Actions'),
            );
          }
        },
      );
    }
  },
});
