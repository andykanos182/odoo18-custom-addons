/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState, onMounted } from "@odoo/owl";

export class ProductKanbanDesktopController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.desktopState = useState({
            pricelists: [],
            selectedPricelistId: "",
        });

        onWillStart(async () => {
            await this.fetchPricelists();
            const currentContext = (this.env.searchModel && this.env.searchModel.context) || {};
            if (currentContext.pricelist) {
                // Respect existing pricelist in current search context
                this.desktopState.selectedPricelistId = String(currentContext.pricelist);
            } else if (this.desktopState.pricelists && this.desktopState.pricelists.length) {
                // Default to the first pricelist in the returned list (top-most shown)
                this.desktopState.selectedPricelistId = String(this.desktopState.pricelists[0].id);
                // Do NOT apply context here: applying during onWillStart can happen
                // before the view/search-model is fully initialized and lead to
                // core code accessing undefined internals (causes slice errors).
                // We'll apply the default on mount instead.
            }
        });

        // Apply the default pricelist only after the component is mounted and
        // the searchModel/config is fully available. This avoids calling
        // `model.load()` too early which triggers internal config parsing.
        onMounted(() => {
            try {
                const currentContext = (this.env.searchModel && this.env.searchModel.context) || {};
                if (!currentContext.pricelist && this.desktopState.selectedPricelistId) {
                    this.updateViewWithContextAndDomain();
                }
            } catch (e) {
                // swallow; non-critical
            }
        });
    }

    async fetchPricelists() {
        try {
            const pricelists = await this.orm.searchRead(
                "product.pricelist", [], ["id", "name"]
            );
            this.desktopState.pricelists = pricelists;
        } catch (e) {
            console.error("Error loading pricelists:", e);
        }
    }

    onPricelistChange(ev) {
        const val = ev.target.value;
        this.desktopState.selectedPricelistId = val;
        this.updateViewWithContextAndDomain();
    }

    updateViewWithContextAndDomain() {
        const pricelistId = this.desktopState.selectedPricelistId
            ? parseInt(this.desktopState.selectedPricelistId)
            : undefined;

        if (this.model && this.model.config) {
            if (!this.model.config.context) {
                this.model.config.context = {};
            }
            if (pricelistId) {
                this.model.config.context.pricelist = pricelistId;
            } else {
                delete this.model.config.context.pricelist;
            }
        }

        if (this.env.searchModel) {
            let newContext = { ...(this.env.searchModel.context || {}) };
            if (pricelistId) {
                newContext.pricelist = pricelistId;
            } else {
                delete newContext.pricelist;
            }
            try {
                this.env.searchModel.update({ context: newContext });
            } catch (e) {
                // ignore
            }
        }

        if (this.model && typeof this.model.load === "function") {
            try {
                const p = this.model.load();
                if (p && typeof p.then === "function") {
                    p.catch((err) => console.warn("ProductKanbanDesktop: model.load() failed:", err));
                }
            } catch (err) {
                console.warn("ProductKanbanDesktop: model.load() threw:", err);
            }
        }
    }
}
