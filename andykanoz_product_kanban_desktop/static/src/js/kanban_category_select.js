/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Read-only category display widget for Kanban cards.
 * Shows "Label: value1, value2" as plain text — no edit, no ORM calls.
 * Works with many2one (categ_id) and many2many (public_categ_ids, pos_categ_ids).
 */
export class KanbanCategorySelectField extends Component {
    static template = "andykanoz_product_kanban_desktop.KanbanCategorySelectField";
    static props = { ...standardFieldProps };

    get fieldLabel() {
        const fieldDef = this.props.record.fields[this.props.name];
        return fieldDef ? (fieldDef.string || this.props.name) : this.props.name;
    }

    get fieldType() {
        const fieldDef = this.props.record.fields[this.props.name];
        return fieldDef ? fieldDef.type : "many2one";
    }

    get isMany2Many() {
        return this.fieldType === "many2many" || this.fieldType === "one2many";
    }

    /**
     * Return a display string for the field value.
     * - many2one: "Category Name" or "-"
     * - many2many: "Cat1, Cat2, Cat3" or "-"
     */
    get displayValue() {
        const val = this.props.record.data[this.props.name];
        if (!val) return "-";

        if (this.isMany2Many) {
            // x2many record list
            if (val.records && val.records.length) {
                const names = val.records.map((r) => {
                    return r.data?.display_name || r.data?.name || "";
                }).filter(Boolean);
                return names.length ? names.join(", ") : "-";
            }
            return "-";
        }

        // many2one
        if (val && typeof val === "object") {
            if (val.display_name) return val.display_name;
            if (Array.isArray(val) && val.length >= 2) return val[1];
        }
        if (Array.isArray(val) && val.length >= 2) {
            return val[1];
        }
        return "-";
    }
}

registry.category("fields").add("kanban_category_select", {
    component: KanbanCategorySelectField,
});
