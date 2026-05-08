/** @odoo-module **/

import { Component } from "@odoo/owl";
import { QtyStepper } from "./qty_stepper";

/**
 * LineCard — one purchase order line rendered as an editable card.
 *
 * Phase 4b: qty stepper + UoM/packaging select + unit price input +
 * expiry date input with near-expiry warning coloring.
 *
 * Props:
 *   line — line object from POEditor.state.lines[i]. Fields:
 *     clientId, product, productQty, productUom, productPackaging,
 *     productPackagingQty, priceUnit, priceSubtotal,
 *     expectedExpiryDate, requiresExpiry, _packagings, _uoms.
 *   onChange(clientId, patch) — apply partial update to the line.
 *   onRemove(clientId) — remove the line.
 *   currency — { symbol, decimalPlaces }.
 */
export class LineCard extends Component {
    static template = "andykanoz_purchase_mobile.LineCard";
    static components = { QtyStepper };
    static props = {
        line: { type: Object },
        onChange: { type: Function },
        onRemove: { type: Function },
        currency: { type: Object, optional: true },
        expiryWarningDays: { type: Number, optional: true },
    };
    static defaultProps = {
        currency: { symbol: "Rp", decimalPlaces: 0 },
        expiryWarningDays: 60,
    };

    // ---- Event handlers ----

    onRemoveClick() {
        this.props.onRemove(this.props.line.clientId);
    }

    onQtyChange(newQty) {
        this._patch({
            productQty: newQty,
            priceSubtotal: newQty * (this.props.line.priceUnit || 0),
        });
    }

    onUomChange(ev) {
        const uomId = parseInt(ev.target.value, 10);
        const uoms = this.props.line._uoms || [];
        const uom = uoms.find((u) => u && u.id === uomId);
        if (uom) this._patch({ productUom: uom });
    }

    onPackagingChange(ev) {
        const pkgId = parseInt(ev.target.value, 10);
        const pkgs = this.props.line._packagings || [];
        if (!pkgId) {
            this._patch({ productPackaging: null });
            return;
        }
        const pkg = pkgs.find((p) => p && p.id === pkgId);
        if (pkg) this._patch({ productPackaging: pkg });
    }

    onPriceChange(ev) {
        const raw = (ev.target.value || "").replace(/\./g, "").replace(",", ".");
        const parsed = parseFloat(raw);
        if (isFinite(parsed) && parsed >= 0) {
            this._patch({
                priceUnit: parsed,
                priceSubtotal: parsed * (this.props.line.productQty || 0),
            });
        } else {
            ev.target.value = this.formatPrice(this.props.line.priceUnit);
        }
    }

    onExpiryChange(ev) {
        const raw = ev.target.value || null;
        this._patch({ expectedExpiryDate: raw });
    }

    _patch(partial) {
        this.props.onChange(this.props.line.clientId, partial);
    }

    // ---- Formatting ----

    formatMoney(amount) {
        const symbol = this.props.currency.symbol || "Rp";
        const n = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0,
        }).format(Math.round(amount || 0));
        return symbol + " " + n;
    }

    formatPrice(amount) {
        // Used in the unit-price input — same rounding but without
        // the currency symbol, since the symbol is rendered in a
        // sibling element as a prefix.
        return new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0,
        }).format(Math.round(amount || 0));
    }

    // ---- Expiry badge classification ----

    get expiryBadge() {
        const line = this.props.line;
        if (!line.requiresExpiry) {
            return { label: "Tanpa expired", cls: "pm-badge-idle" };
        }
        if (!line.expectedExpiryDate) {
            return { label: "Isi tanggal expired", cls: "pm-badge-wait" };
        }
        const exp = new Date(line.expectedExpiryDate);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const diffDays = Math.round((exp - today) / (24 * 3600 * 1000));
        const datePart = this.formatExpiryLabel(exp);
        if (diffDays < 0) {
            return { label: datePart + " · kadaluarsa", cls: "pm-badge-err" };
        }
        if (diffDays <= this.props.expiryWarningDays) {
            return { label: datePart + " · dekat", cls: "pm-badge-err" };
        }
        return { label: datePart, cls: "pm-badge-run" };
    }

    formatExpiryLabel(d) {
        return "Exp: " + d.toLocaleDateString("id-ID", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }

    // ---- Option list helpers ----

    get uomOptions() {
        // Deduplicate by id — uom_id and uom_po_id can match.
        const uoms = this.props.line._uoms || [];
        const seen = new Set();
        const out = [];
        for (const u of uoms) {
            if (!u || seen.has(u.id)) continue;
            seen.add(u.id);
            out.push(u);
        }
        return out;
    }

    get packagingOptions() {
        return this.props.line._packagings || [];
    }

    get currentUomId() {
        return (this.props.line.productUom && this.props.line.productUom.id) || "";
    }

    get currentPackagingId() {
        return (this.props.line.productPackaging && this.props.line.productPackaging.id) || "";
    }
}
