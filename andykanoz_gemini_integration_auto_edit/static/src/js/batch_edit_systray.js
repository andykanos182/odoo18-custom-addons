/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BatchEditSystray extends Component {
    static template = "andykanoz_gemini_integration_auto_edit.BatchEditSystray";
    static props = {};

    setup() {
        this.batchEditService = useService("batchEditService");
    }

    get job() {
        return this.batchEditService.currentJob;
    }

    get isVisible() {
        return !!this.job;
    }

    get processed() {
        return (this.job && (this.job.processed + this.job.failed)) || 0;
    }
    get total() {
        return (this.job && this.job.total) || 0;
    }
    get state() {
        return (this.job && this.job.state) || "";
    }

    get cssClass() {
        const base = "o_andykanoz_gemini_integration_auto_edit_systray";
        if (this.state === "done") return base + " o_state_done";
        if (this.state === "failed") return base + " o_state_failed";
        if (this.state === "cancelled") return base + " o_state_cancelled";
        return base;
    }

    onClick() {
        this.batchEditService.openDialog();
    }
}

registry.category("systray").add(
    "andykanoz_gemini_integration_auto_edit.Systray",
    { Component: BatchEditSystray },
    { sequence: 99 }
);
