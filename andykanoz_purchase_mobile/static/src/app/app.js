/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { POList } from "../components/po_list";
import { VendorPicker } from "../components/vendor_picker";

/**
 * Root component for the Purchase Mobile app.
 *
 * Phase 3 exposes two views via a top tab bar:
 *   - 'list'       : POList (draft / confirmed / all purchase orders)
 *   - 'vendor_demo': VendorPicker standalone demo, so the autocomplete
 *                    can be exercised before it's wired into POEditor
 *                    in Phase 4.
 *
 * Later phases will replace the tab bar with a proper router + header
 * (back button, PO ref, save/confirm actions) once POEditor lands.
 */
export class PurchaseMobileApp extends Component {
    static template = "andykanoz_purchase_mobile.App";
    static components = { POList, VendorPicker };

    setup() {
        this.state = useState({
            view: "list",
            // Used by the VendorPicker demo tab so we can show the
            // currently-selected vendor underneath the picker.
            demoSelectedVendor: null,
        });
    }

    showView(view) {
        this.state.view = view;
    }

    onDemoVendorSelected(vendor) {
        this.state.demoSelectedVendor = vendor;
    }

    get demoSelectedVendorJson() {
        return this.state.demoSelectedVendor
            ? JSON.stringify(this.state.demoSelectedVendor, null, 2)
            : "";
    }
}
