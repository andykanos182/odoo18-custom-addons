/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const TERMINAL = ["done", "cancelled", "failed"];

export class BatchEditProgressDialog extends Component {
    static template = "andykanoz_gemini_integration_auto_edit.BatchEditProgressDialog";
    static components = { Dialog };
    static props = {
        getJob: Function,
        onCancel: Function,
        close: Function,
    };

    setup() {
        this.batchEditService = useService("batchEditService");
    }

    get job() {
        return this.props.getJob() || this.batchEditService.currentJob;
    }

    get total() {
        return (this.job && this.job.total) || 0;
    }
    get processed() {
        return (this.job && this.job.processed) || 0;
    }
    get failed() {
        return (this.job && this.job.failed) || 0;
    }
    get state() {
        return (this.job && this.job.state) || "draft";
    }
    get currentProductName() {
        return (this.job && this.job.current_product_name) || "";
    }
    get progressPercent() {
        if (!this.total) {
            return 0;
        }
        return Math.round(((this.processed + this.failed) / this.total) * 100);
    }
    get isTerminal() {
        return TERMINAL.includes(this.state);
    }
    get statusLabel() {
        switch (this.state) {
            case "done":
                return "Completed";
            case "cancelled":
                return "Cancelled";
            case "failed":
                return "Failed";
            case "running":
                return "Running";
            default:
                return "Pending";
        }
    }

    onClickHide() {
        this.props.close();
    }

    async onClickCancel() {
        if (this.isTerminal) {
            this.props.close();
            return;
        }
        await this.props.onCancel();
    }
}
