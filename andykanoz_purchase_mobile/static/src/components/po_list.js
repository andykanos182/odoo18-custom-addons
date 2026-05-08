/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { jsonRpc } from "../services/rpc";

/**
 * Lists purchase orders filtered by state. Fetches from
 *   POST /andykanoz_purchase_mobile/api/pos/list
 *
 * Phase 3: read-only. Tapping a card pops an alert as a placeholder
 * for the Phase 4 POEditor routing. Filter pills at the top switch
 * between draft / confirmed / all states.
 */
export class POList extends Component {
    static template = "andykanoz_purchase_mobile.POList";

    setup() {
        this.state = useState({
            loading: true,
            error: null,
            orders: [],
            count: 0,
            // '' means "all states" — the backend skips the filter.
            filter: "draft",
        });
        onWillStart(() => this.loadOrders());
    }

    async loadOrders() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const result = await jsonRpc(
                "/andykanoz_purchase_mobile/api/pos/list",
                { state: this.state.filter || false, limit: 50 }
            );
            this.state.orders = result.orders || [];
            this.state.count = result.count || 0;
        } catch (err) {
            this.state.error = err.message;
            this.state.orders = [];
            this.state.count = 0;
        } finally {
            this.state.loading = false;
        }
    }

    async changeFilter(filter) {
        if (this.state.filter === filter) return;
        this.state.filter = filter;
        await this.loadOrders();
    }

    formatMoney(amount, currency) {
        const symbol = (currency && currency.symbol) || "Rp";
        const rounded = Math.round(amount || 0);
        return `${symbol} ${rounded.toLocaleString("id-ID")}`;
    }

    formatDate(dt) {
        if (!dt) return "—";
        const d = new Date(dt.replace(" ", "T"));
        if (isNaN(d.getTime())) return dt;
        return d.toLocaleDateString("id-ID", {
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }

    stateBadgeClass(state) {
        const map = {
            draft: "badge-wait",
            sent: "badge-wait",
            "to approve": "badge-run",
            purchase: "badge-ok",
            done: "badge-ok",
            cancel: "badge-err",
        };
        return map[state] || "badge-wait";
    }

    onTapOrder(order) {
        // Phase 4 will route this to the POEditor. For now, show a
        // simple summary so we can confirm the tap wiring works.
        const lines = [
            `PO: ${order.name}`,
            `State: ${order.state_label}`,
            `Vendor: ${order.partner ? order.partner.name : "—"}`,
            `Items: ${order.line_count}`,
            `Total: ${this.formatMoney(order.amount_total, order.currency)}`,
        ];
        if (order.created_via_mobile) {
            lines.push("Source: mobile");
        }
        alert(lines.join("\n") + "\n\n(Phase 4: POEditor akan terbuka di sini)");
    }
}
