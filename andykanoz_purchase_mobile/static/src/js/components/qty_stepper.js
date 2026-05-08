/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * QtyStepper — compact `− N +` control.
 *
 * Props:
 *   value    — number, current qty
 *   onChange — called with the new number when it changes
 *   step     — increment (default 1)
 *   min      — minimum value (default 0)
 *   precision — decimal places shown in the input (default 2)
 *
 * We use inputmode="decimal" so mobile keyboards show the numeric
 * keypad and an id-ID-formatted string so "1,50" renders naturally.
 * On blur the input is re-normalized so users get consistent display.
 */
export class QtyStepper extends Component {
    static template = "andykanoz_purchase_mobile.QtyStepper";
    static props = {
        value: { type: Number },
        onChange: { type: Function },
        step: { type: Number, optional: true },
        min: { type: Number, optional: true },
        precision: { type: Number, optional: true },
    };
    static defaultProps = {
        step: 1,
        min: 0,
        precision: 2,
    };

    get formattedValue() {
        return new Intl.NumberFormat("id-ID", {
            minimumFractionDigits: this.props.precision,
            maximumFractionDigits: this.props.precision,
        }).format(this.props.value || 0);
    }

    onMinusClick() {
        const next = Math.max(
            this.props.min,
            (this.props.value || 0) - this.props.step
        );
        this.props.onChange(this._round(next));
    }

    onPlusClick() {
        const next = (this.props.value || 0) + this.props.step;
        this.props.onChange(this._round(next));
    }

    onInputChange(ev) {
        // Accept both "1.5" and "1,5" (Indonesian locale)
        const raw = (ev.target.value || "").replace(/\./g, "").replace(",", ".");
        const parsed = parseFloat(raw);
        if (isFinite(parsed) && parsed >= this.props.min) {
            this.props.onChange(this._round(parsed));
        } else {
            // Reset display to last known good value
            ev.target.value = this.formattedValue;
        }
    }

    _round(n) {
        const m = Math.pow(10, this.props.precision);
        return Math.round(n * m) / m;
    }
}
