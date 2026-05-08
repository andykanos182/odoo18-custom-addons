/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";

/**
 * Default action xml-id for the standard Inventory > Products (Odoo built-in).
 * Used to redirect users back to the native kanban when they click the
 * default kanban button while inside our Desktop Kanban action.
 */
const DEFAULT_PRODUCT_ACTION_XMLID = "stock.product_template_action_product";

patch(ControlPanel.prototype, {
    setup() {
        super.setup(...arguments);
        this._akdNavigating = false;
    },

    /**
     * Show the desktop kanban button on both product.template and product.product views.
     */
    get showDesktopKanbanButton() {
        const resModel = this.env.searchModel && this.env.searchModel.resModel;
        return resModel === "product.template" || resModel === "product.product";
    },

    /**
     * Return true when currently inside the desktop kanban action.
     */
    get isDesktopKanbanActive() {
        const cfg = this.env.config;
        if (!cfg) return false;
        if (cfg.viewArch && cfg.viewArch.getAttribute
            && cfg.viewArch.getAttribute("js_class") === "product_kanban_desktop") {
            return true;
        }
        if (cfg.actionXmlId === "andykanoz_product_kanban_desktop.action_product_desktop_kanban" ||
            cfg.actionXmlId === "andykanoz_product_kanban_desktop.action_product_product_desktop_kanban") {
            return true;
        }
        return false;
    },

    async openDesktopKanban() {
        if (this.isDesktopKanbanActive || this._akdNavigating) {
            return;
        }
        this._akdNavigating = true;
        try {
            const resModel = this.env.searchModel && this.env.searchModel.resModel;
            const actionXmlId = resModel === 'product.product'
                ? 'andykanoz_product_kanban_desktop.action_product_product_desktop_kanban'
                : 'andykanoz_product_kanban_desktop.action_product_desktop_kanban';
            await this.actionService.doAction(
                actionXmlId,
                { stackPosition: "replaceCurrentAction" }
            );
        } catch (e) {
            console.warn("Desktop Kanban navigation failed:", e);
        } finally {
            this._akdNavigating = false;
        }
    },

    /**
     * Redirect user to the native Inventory > Products action with kanban view.
     * Called when user clicks the built-in kanban button while inside our
     * Desktop Kanban action.
     */
    async openDefaultKanban() {
        if (this._akdNavigating) {
            return;
        }
        this._akdNavigating = true;
        try {
            await this.actionService.doAction(
                DEFAULT_PRODUCT_ACTION_XMLID,
                {
                    stackPosition: "replaceCurrentAction",
                    viewType: "kanban",
                }
            );
        } catch (e) {
            console.warn("Default kanban navigation failed:", e);
        } finally {
            this._akdNavigating = false;
        }
    },

    /**
     * Capture-phase click handler on the view switcher <nav>.
     * When user is inside Desktop Kanban action AND clicks the default
     * Odoo kanban button (NOT our custom one), we intercept and redirect
     * to the native Inventory > Products action.
     *
     * Our own button has class `akd_desktop_kanban_btn` so we can exclude it.
     */
    onAkdSwitchNavClick(ev) {
        if (!this.isDesktopKanbanActive) return;

        const btn = ev.target.closest("button.o_switch_view");
        if (!btn) return;

        // Skip our own Desktop Kanban button - let its own handler run
        if (btn.classList.contains("akd_desktop_kanban_btn")) return;

        // Detect if this is the default kanban button
        // (Odoo renders it with icon .oi-view-kanban or class .o_kanban)
        const isKanbanBtn =
            btn.classList.contains("o_kanban") ||
            btn.querySelector(".oi-view-kanban") ||
            btn.querySelector(".fa-th") ||
            btn.getAttribute("data-tooltip") === "Kanban";

        if (isKanbanBtn) {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
            this.openDefaultKanban();
        }
        // list/form switches within our action are fine
    },
});
