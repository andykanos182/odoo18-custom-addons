/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { rpc } from "../services/rpc_service";

/**
 * POList — read-only browse of draft Purchase Orders.
 *
 * Phase 3: used as a standalone demo component on the Phase 3 page.
 * Phase 4+: will become the "list view" in the main app, where tapping
 * an order opens POEditor.
 *
 * Props:
 *   state     — 'draft' (default), 'purchase', 'done', or array.
 *   limit     — max rows (default 50).
 *   mobileOnly — if true, only fetch POs created via mobile (MP prefix).
 *   onPickOrder(order) — optional callback when user taps an item.
 */
export class POList extends Component {
    static template = "andykanoz_purchase_mobile.POList";
    static props = {
        stateFilter: { type: [String, Array], optional: true },
        limit: { type: Number, optional: true },
        mobileOnly: { type: Boolean, optional: true },
        onPickOrder: { type: Function, optional: true },
    };
    static defaultProps = {
        stateFilter: "draft",
        limit: 50,
        mobileOnly: false,
    };

    setup() {
        this.state = useState({
            orders: [],
            loading: true,
            error: null,
        });
        onMounted(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await rpc(
                "/andykanoz_purchase_mobile/api/pos/list",
                {
                    state: this.props.stateFilter,
                    limit: this.props.limit,
                    mobile_only: this.props.mobileOnly,
                }
            );
            this.state.orders = result.orders || [];
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.loading = false;
        }
    }

    onItemClick(order) {
        if (this.props.onPickOrder) {
            this.props.onPickOrder(order);
        }
    }

    formatMoney(amount, currency) {
        const symbol = (currency && currency.symbol) || "Rp";
        const n = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0,
        }).format(Math.round(amount || 0));
        return symbol + " " + n;
    }

    formatDate(dateStr) {
        if (!dateStr) return "—";
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        return d.toLocaleDateString("id-ID", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }
}
