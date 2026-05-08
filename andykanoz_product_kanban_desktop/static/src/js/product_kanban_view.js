/** @odoo-module **/

import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { ProductKanbanDesktopController } from "./product_kanban_controller";

export const productKanbanDesktopView = {
    ...kanbanView,
    Controller: ProductKanbanDesktopController,
    buttonTemplate: "andykanoz_product_kanban_desktop.buttons",
};

registry.category("views").add("product_kanban_desktop", productKanbanDesktopView);
