/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { POList } from "./components/po_list";
import { POEditor } from "./components/po_editor";

/**
 * PurchaseMobileApp — root OWL component.
 *
 * Phase 4a role: routes between two views:
 *   - 'list'   → shows POList (draft PO browser + "New PO" button)
 *   - 'editor' → shows POEditor for the current PO
 *
 * Navigation is entirely client-side state — no URL routing yet.
 * We'll add hash-based routing when the app grows more views.
 */
export class PurchaseMobileApp extends Component {
    static template = "andykanoz_purchase_mobile.App";
    static components = { POList, POEditor };
    static props = {
        initialData: { type: Object, optional: true },
    };

    setup() {
        const data = this.props.initialData || {};
        this.state = useState({
            user: {
                name: data.userName || "—",
                login: data.userLogin || "—",
            },
            phase: data.phase || "Phase 4a",
            moduleVersion: data.moduleVersion || "18.0.1.0.0",

            // Navigation state
            view: "list",        // 'list' | 'editor'
            currentPoId: null,   // number | null. null = new PO.
        });
    }

    // ---- Navigation ----

    openNewEditor() {
        this.state.currentPoId = null;
        this.state.view = "editor";
    }

    openExistingEditor(order) {
        this.state.currentPoId = order.id;
        this.state.view = "editor";
    }

    backToList() {
        this.state.view = "list";
        this.state.currentPoId = null;
    }
}
