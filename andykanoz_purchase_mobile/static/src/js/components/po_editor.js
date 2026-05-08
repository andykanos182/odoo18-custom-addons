/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { rpc } from "../services/rpc_service";
import { VendorPicker } from "./vendor_picker";
import { ProductPicker } from "./product_picker";
import { LineCard } from "./line_card";

/**
 * POEditor — core editor for a Purchase Order.
 *
 * Phase 4a scope (this iteration):
 *   - Header with back button, PO ref label, save button (stub)
 *   - VendorPicker (locked once the first line is added)
 *   - List of LineCard components (basic version)
 *   - "Add Product" button → opens ProductPicker modal
 *   - Footer with untaxed + total
 *
 * Phase 4b will polish LineCard (qty stepper, expiry input, packaging).
 * Phase 6 will wire in the save/confirm endpoints. For now the editor
 * state lives entirely client-side.
 *
 * Props:
 *   poId — number | null. null = new PO, number = edit existing.
 *   onBack — function, called when user taps the back button.
 */
export class POEditor extends Component {
    static template = "andykanoz_purchase_mobile.POEditor";
    static components = { VendorPicker, ProductPicker, LineCard };
    static props = {
        poId: { type: [Number, { value: null }], optional: true },
        onBack: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({
            loading: !!this.props.poId,
            error: null,
            // Order-level state
            order: {
                id: this.props.poId || null,
                name: this.props.poId ? "..." : "New PO",
                state: "draft",
                stateLabel: "Draft",
                partner: null,
                currency: { symbol: "Rp", decimalPlaces: 0 },
                createdViaMobile: !this.props.poId, // new = mobile-born
            },
            lines: [],
            // Frontend-only config: how many days before expiry counts
            // as "near" (red badge). Populated from ir.config_parameter
            // by the first response that includes it (po/get on edit,
            // or products/search on add-line for new POs). Default 60
            // matches the backend default in _get_expiry_warning_days.
            expiryWarningDays: 60,
            // UI state
            showProductPicker: false,
            saving: false,
            confirming: false,
            deleting: false,
            saveError: null,
            dirty: false, // true once the user has made any change
        });
        if (this.props.poId) {
            this.loadExisting();
        }
    }

    async loadExisting() {
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/po/get",
                { po_id: this.props.poId }
            );
            if (result.error) {
                this.state.error = "PO not found (id=" + this.props.poId + ")";
                return;
            }
            if (typeof result.expiry_warning_days === "number") {
                this.state.expiryWarningDays = result.expiry_warning_days;
            }
            const o = result.order;
            this.state.order = {
                id: o.id,
                name: o.name,
                state: o.state,
                stateLabel: o.state_label,
                partner: o.partner,
                currency: {
                    symbol: (o.currency && o.currency.symbol) || "Rp",
                    decimalPlaces: (o.currency && o.currency.decimal_places) || 0,
                },
                createdViaMobile: o.created_via_mobile,
            };
            this.state.lines = (o.lines || []).map(line => ({
                // Stable client-side ID. Negative for client-only lines
                // (not yet persisted); server PK for loaded lines.
                clientId: "srv-" + line.id,
                serverId: line.id,
                product: line.product,
                productQty: line.product_qty,
                productUom: line.product_uom,
                productPackaging: line.product_packaging,
                productPackagingQty: line.product_packaging_qty,
                priceUnit: line.price_unit,
                priceSubtotal: line.price_subtotal,
                expectedExpiryDate: line.x_expected_expiry_date,
                requiresExpiry: line.requires_expiry,
            }));
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.loading = false;
        }
    }

    // ---- Vendor handling ----

    onVendorSelected(vendor) {
        this.state.order.partner = vendor;
        this.state.dirty = true;
    }

    get vendorLocked() {
        return this.state.lines.length > 0;
    }

    // ---- Line handling ----

    openProductPicker() {
        if (!this.state.order.partner) {
            alert("Pilih vendor terlebih dahulu sebelum menambah produk.");
            return;
        }
        this.state.showProductPicker = true;
    }

    closeProductPicker() {
        this.state.showProductPicker = false;
    }

    onConfigUpdate(config) {
        // Called by ProductPicker when its search response carries
        // server-provided settings we want to capture (currently just
        // expiryWarningDays). Idempotent.
        if (typeof config.expiryWarningDays === "number") {
            this.state.expiryWarningDays = config.expiryWarningDays;
        }
    }

    onProductPicked(product) {
        this.state.showProductPicker = false;
        // Add as a fresh client-side line. No server call yet.
        const clientId = "cli-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);

        // ---- Packaging resolution ----
        // If the user scanned a packaging barcode (e.g. the box label
        // instead of the unit barcode), the backend marks the matched
        // product with `matched_packaging_id`. We pick the packaging
        // row by id and convert qty: 1 box → packaging.qty units.
        // Without a packaging match, fall back to the prior behavior:
        // pre-select the first available packaging (often "none") and
        // qty = 1 unit. The latter is what the user saw before this
        // feature, so existing flows are unchanged.
        const packagings = product.packagings || [];
        let chosenPackaging = null;
        let qty = 1.0;
        let packagingQty = 0;

        if (product.matched_packaging_id) {
            chosenPackaging = packagings.find(
                (p) => p.id === product.matched_packaging_id
            ) || null;
            if (chosenPackaging) {
                // 1 box scanned = 1 "packaging unit". Multiply by
                // packaging.qty to get the line's product_qty in the
                // base UoM — matches Odoo's standard packaging math.
                packagingQty = 1;
                qty = (chosenPackaging.qty || 1) * packagingQty;
            }
        }
        if (!chosenPackaging) {
            // Default: pre-select first packaging if any, qty = 1 unit.
            chosenPackaging = packagings.length ? packagings[0] : null;
        }

        const priceUnit = product.unit_price || product.standard_price || 0;
        this.state.lines.push({
            clientId,
            serverId: null,
            product: {
                id: product.id,
                name: product.name,
                display_name: product.display_name,
                default_code: product.default_code,
                image_url: product.image_url,
            },
            productQty: qty,
            productUom: product.uom_po_id || product.uom_id,
            productPackaging: chosenPackaging,
            productPackagingQty: packagingQty,
            priceUnit,
            priceSubtotal: priceUnit * qty,
            expectedExpiryDate: null,
            requiresExpiry: !!product.requires_expiry,
            // Holding the product's full packagings list so LineCard can
            // render the packaging selector without extra round-trips.
            _packagings: packagings,
            // Full list of UoMs (filtered to product's UoM category) the
            // user can switch between. Comes from the server's
            // _serialize_uom_options() so existing PO loads, search
            // results, and add-line all share the same source of truth.
            _uoms: product.uom_options || [
                product.uom_id,
                product.uom_po_id,
            ].filter(Boolean),
        });
        this.state.dirty = true;
    }

    onLineRemove(clientId) {
        const idx = this.state.lines.findIndex(l => l.clientId === clientId);
        if (idx >= 0) {
            this.state.lines.splice(idx, 1);
            this.state.dirty = true;
        }
    }

    onLineChange(clientId, patch) {
        const line = this.state.lines.find(l => l.clientId === clientId);
        if (!line) return;
        Object.assign(line, patch);
        this.state.dirty = true;
    }

    // ---- Totals ----

    get untaxedAmount() {
        return this.state.lines.reduce(
            (sum, l) => sum + (l.priceSubtotal || 0),
            0
        );
    }

    get totalAmount() {
        // Taxes hidden by design (decision F). Total = untaxed for now.
        return this.untaxedAmount;
    }

    // ---- Save / Confirm / Delete (Phase 6) ----

    /**
     * Turn our client-side line shape into the minimal payload the
     * /api/po/save endpoint expects. Keeps undefined fields out so
     * _build_line_vals on the backend doesn't confuse null vs absent.
     */
    _lineToPayload(line) {
        const payload = {
            // id = null marks a client-only line (not yet persisted).
            // The backend treats that as "create new line on this PO".
            id: line.serverId || null,
            product_id: line.product.id,
            product_qty: line.productQty,
            price_unit: line.priceUnit,
            product_uom_id:
                (line.productUom && line.productUom.id) || undefined,
            product_packaging_id:
                (line.productPackaging && line.productPackaging.id) || null,
            product_packaging_qty: line.productPackagingQty || 0,
            expected_expiry_date: line.expectedExpiryDate || null,
        };
        return payload;
    }

    /**
     * Replace state.order and state.lines from a fresh server
     * response. Same transform as loadExisting(), factored out so
     * onSave / onConfirm can reuse it.
     */
    _applyServerOrder(result) {
        if (typeof result.expiry_warning_days === "number") {
            this.state.expiryWarningDays = result.expiry_warning_days;
        }
        const o = result.order;
        this.state.order = {
            id: o.id,
            name: o.name,
            state: o.state,
            stateLabel: o.state_label,
            partner: o.partner,
            currency: {
                symbol: (o.currency && o.currency.symbol) || "Rp",
                decimalPlaces: (o.currency && o.currency.decimal_places) || 0,
            },
            createdViaMobile: o.created_via_mobile,
        };
        this.state.lines = (o.lines || []).map((line) => ({
            clientId: "srv-" + line.id,
            serverId: line.id,
            product: line.product,
            productQty: line.product_qty,
            productUom: line.product_uom,
            productPackaging: line.product_packaging,
            productPackagingQty: line.product_packaging_qty,
            priceUnit: line.price_unit,
            priceSubtotal: line.price_subtotal,
            expectedExpiryDate: line.x_expected_expiry_date,
            requiresExpiry: line.requires_expiry,
            // Phase "uom-fix": po/get now ships uom_options and
            // packagings on each line, so we use those directly.
            // Old default of [line.product_uom] left the dropdown
            // stuck on the saved value with no other choice.
            _packagings: line.packagings || [],
            _uoms: line.uom_options || (
                line.product_uom ? [line.product_uom] : []
            ),
        }));
        this.state.dirty = false;
        this.state.saveError = null;
    }

    async onSave() {
        if (this.state.saving) return;
        if (!this.state.order.partner) {
            this.state.saveError = "Pilih vendor terlebih dahulu.";
            return;
        }
        if (!this.state.lines.length) {
            this.state.saveError = "Tambahkan minimal satu produk.";
            return;
        }
        this.state.saving = true;
        this.state.saveError = null;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/po/save",
                {
                    po_id: this.state.order.id || null,
                    vendor_id: this.state.order.partner.id,
                    lines: this.state.lines.map((l) => this._lineToPayload(l)),
                }
            );
            if (result.error) {
                this.state.saveError = "Gagal simpan: " + result.error;
                return;
            }
            this._applyServerOrder(result);
        } catch (e) {
            this.state.saveError = e.message || String(e);
        } finally {
            this.state.saving = false;
        }
    }

    async onConfirm() {
        if (this.state.confirming) return;
        if (!this.state.order.id) {
            this.state.saveError = "Save dulu sebelum confirm.";
            return;
        }
        if (this.state.dirty) {
            this.state.saveError =
                "Ada perubahan yang belum disimpan. Save dulu lalu confirm.";
            return;
        }
        if (!confirm("Confirm PO " + this.state.order.name + "? Setelah confirm, PO tidak bisa diedit di Purchase Mobile lagi.")) {
            return;
        }
        this.state.confirming = true;
        this.state.saveError = null;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/po/confirm",
                { po_id: this.state.order.id }
            );
            if (result.error) {
                this.state.saveError = "Gagal confirm: " + result.error;
                return;
            }
            this._applyServerOrder(result);
            // Confirmed POs don't belong in the draft browser any more;
            // pop back to the list so the user doesn't sit on a stale
            // editor for a non-draft order.
            if (this.props.onBack) this.props.onBack();
        } catch (e) {
            this.state.saveError = e.message || String(e);
        } finally {
            this.state.confirming = false;
        }
    }

    async onDelete() {
        if (this.state.deleting) return;
        if (!this.state.order.id) return;
        if (!confirm("Hapus draft PO " + this.state.order.name + "? Aksi ini tidak bisa dibatalkan.")) {
            return;
        }
        this.state.deleting = true;
        this.state.saveError = null;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/po/delete",
                { po_id: this.state.order.id }
            );
            if (result.error) {
                this.state.saveError = "Gagal hapus: " + result.error;
                return;
            }
            if (this.props.onBack) this.props.onBack();
        } catch (e) {
            this.state.saveError = e.message || String(e);
        } finally {
            this.state.deleting = false;
        }
    }

    // ---- Button visibility ----

    get canSave() {
        return (
            this.state.order.state === "draft" &&
            !this.state.saving &&
            !this.state.confirming &&
            !this.state.deleting
        );
    }

    get canConfirm() {
        return (
            !!this.state.order.id &&
            this.state.order.state === "draft" &&
            this.state.lines.length > 0 &&
            !this.state.saving &&
            !this.state.confirming &&
            !this.state.deleting
        );
    }

    get canDelete() {
        return (
            !!this.state.order.id &&
            this.state.order.state === "draft" &&
            !this.state.saving &&
            !this.state.confirming &&
            !this.state.deleting
        );
    }

    onBackClick() {
        if (this.state.dirty) {
            if (!confirm("Ada perubahan yang belum disimpan. Keluar tanpa simpan?")) {
                return;
            }
        }
        if (this.props.onBack) this.props.onBack();
    }

    // ---- Formatting helpers ----

    formatMoney(amount) {
        const symbol = this.state.order.currency.symbol;
        const n = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0,
        }).format(Math.round(amount || 0));
        return symbol + " " + n;
    }
}
