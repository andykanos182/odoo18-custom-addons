/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { rpc } from "../services/rpc_service";

/**
 * VendorPicker — custom autocomplete for selecting a supplier.
 *
 * Follows the pattern established in andykanoz_quick_purchase:
 *   - Plain <input> + <div> dropdown (NOT Odoo's Many2XAutocomplete,
 *     which crashes on mobile Chrome in certain views).
 *   - t-on-mousedown on result rows so it fires BEFORE input blur
 *     dismisses the dropdown — otherwise the click never lands.
 *   - Backend uses name_search with res_partner_search_mode='supplier'
 *     context to match standard Odoo PO vendor selection (includes
 *     partners with supplier_rank = 0).
 *
 * Props:
 *   onSelect(vendor | null) — called when selection changes
 *   initialVendor — optional pre-selected vendor object
 *   placeholder   — input placeholder text
 */
export class VendorPicker extends Component {
    static template = "andykanoz_purchase_mobile.VendorPicker";
    static props = {
        onSelect: { type: Function, optional: true },
        initialVendor: { type: [Object, { value: null }], optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        placeholder: "Cari vendor...",
    };

    setup() {
        this.state = useState({
            query: "",
            results: [],
            showDropdown: false,
            selected: this.props.initialVendor || null,
            isSearching: false,
        });
        this._searchTimer = null;
        this._blurTimer = null;
    }

    onInputChange(ev) {
        this.state.query = ev.target.value;
        this._debouncedSearch();
    }

    onInputFocus() {
        this.state.showDropdown = true;
        if (!this.state.results.length) {
            this._doSearch();
        }
    }

    onInputBlur() {
        // Delay hiding so mousedown on a result row can fire first.
        this._blurTimer = setTimeout(() => {
            this.state.showDropdown = false;
        }, 180);
    }

    _debouncedSearch() {
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this._doSearch(), 250);
    }

    async _doSearch() {
        this.state.isSearching = true;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/vendors",
                { query: this.state.query, limit: 10 }
            );
            this.state.results = result.vendors || [];
        } catch (e) {
            console.error("[VendorPicker] search failed:", e);
            this.state.results = [];
        } finally {
            this.state.isSearching = false;
        }
    }

    onVendorMousedown(vendor) {
        // Using mousedown (not click) so this runs before the input's blur.
        if (this._blurTimer) clearTimeout(this._blurTimer);
        this.state.selected = vendor;
        this.state.query = "";
        this.state.showDropdown = false;
        this.state.results = [];
        if (this.props.onSelect) {
            this.props.onSelect(vendor);
        }
    }

    onClearSelection() {
        this.state.selected = null;
        this.state.query = "";
        this.state.results = [];
        if (this.props.onSelect) {
            this.props.onSelect(null);
        }
    }
}
