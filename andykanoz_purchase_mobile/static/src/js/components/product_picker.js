/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { rpc } from "../services/rpc_service";
import { BarcodeScanner } from "./barcode_scanner";

/**
 * ProductPicker — modal for searching and picking a product.
 *
 * Phase 4a: basic search + tap-to-add. Phase 8 will add a camera
 * barcode scanner button inside this same modal.
 *
 * Props:
 *   vendorId — number | null. If set, the endpoint returns the three-
 *              tier unit price for this vendor. If null, only standard_price.
 *   onPick(product) — called when user taps a product.
 *   onClose — called when user taps the close button / backdrop.
 */
export class ProductPicker extends Component {
    static template = "andykanoz_purchase_mobile.ProductPicker";
    static components = { BarcodeScanner };
    static props = {
        vendorId: { type: [Number, { value: null }], optional: true },
        onPick: { type: Function },
        onClose: { type: Function },
        onConfigUpdate: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            query: "",
            results: [],
            loading: false,
            error: null,
            // Phase 8: barcode scanner overlay visibility. Toggled by
            // the scan button in the search bar.
            showScanner: false,
        });
        this._searchTimer = null;
        this._inputRef = useRef("searchInput");
        onMounted(() => {
            // Auto-focus when modal opens, but wait a tick so transforms
            // settle before keyboard slides up on mobile.
            setTimeout(() => {
                if (this._inputRef.el) this._inputRef.el.focus();
            }, 120);
            this.search();
        });
    }

    // ---- Scanner integration (Phase 8) ----

    get scannerSupported() {
        return BarcodeScanner.isSupported();
    }

    openScanner() {
        this.state.showScanner = true;
    }

    closeScanner() {
        this.state.showScanner = false;
    }

    onBarcodeDetected(text) {
        // Pipe the decoded barcode straight into the search input,
        // close the scanner, and trigger search. If the search returns
        // exactly one result, auto-pick it (the most common case for
        // a unique SKU/EAN). Otherwise just leave the user on the
        // results list — they can tap the right one.
        this.state.query = text;
        if (this._inputRef.el) {
            this._inputRef.el.value = text;
        }
        this.state.showScanner = false;
        this._searchAndMaybeAutoPick();
    }

    async _searchAndMaybeAutoPick() {
        await this.search();
        if (this.state.results.length === 1) {
            this.props.onPick(this.state.results[0]);
        }
    }

    onQueryInput(ev) {
        this.state.query = ev.target.value;
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.search(), 250);
    }

    async search() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/products/search",
                {
                    query: this.state.query,
                    limit: 20,
                    vendor_id: this.props.vendorId || null,
                }
            );
            this.state.results = result.products || [];
            // Bubble up server-provided config so the parent (POEditor)
            // can use the latest expiry_warning_days threshold without a
            // separate fetch. Pattern: piggyback on responses we're
            // already making rather than dedicated /api/config endpoints.
            if (this.props.onConfigUpdate && typeof result.expiry_warning_days === "number") {
                this.props.onConfigUpdate({
                    expiryWarningDays: result.expiry_warning_days,
                });
            }
        } catch (e) {
            this.state.error = e.message;
            this.state.results = [];
        } finally {
            this.state.loading = false;
        }
    }

    onResultClick(product) {
        this.props.onPick(product);
    }

    onBackdropClick(ev) {
        if (ev.target.classList.contains("pm-modal-backdrop")) {
            this.props.onClose();
        }
    }

    formatMoney(amount) {
        const n = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0,
        }).format(Math.round(amount || 0));
        return "Rp " + n;
    }
}
