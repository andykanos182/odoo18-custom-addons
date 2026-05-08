/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { BatchEditProgressDialog } from "./batch_edit_progress_dialog";

const BUS_CHANNEL = "andykanoz_gemini_integration_auto_edit.job_update";

export const batchEditService = {
    dependencies: ["bus_service", "dialog", "notification"],
    start(env, { bus_service, dialog, notification }) {
        const state = reactive({ job: null });
        let closeDialogFn = null;
        let autoCloseHandle = null;

        function applyJob(payload) {
            state.job = payload || null;
            if (autoCloseHandle) {
                clearTimeout(autoCloseHandle);
                autoCloseHandle = null;
            }
            if (payload && ["done", "cancelled", "failed"].includes(payload.state)) {
                autoCloseHandle = setTimeout(() => {
                    if (state.job && state.job.job_id === payload.job_id) {
                        state.job = null;
                    }
                    autoCloseHandle = null;
                }, 5000);
            }
        }

        bus_service.subscribe(BUS_CHANNEL, (payload) => {
            applyJob(payload);
        });
        bus_service.start();

        // Restore state on startup
        (async () => {
            try {
                const active = await rpc("/andykanoz_gemini_integration_auto_edit/get_active_job");
                if (active) {
                    applyJob(active);
                }
            } catch (e) {
                console.warn("[andykanoz_gemini_integration_auto_edit] restore failed", e);
            }
        })();

        const service = {
            get state() {
                return state;
            },
            get currentJob() {
                return state.job;
            },
            openDialog() {
                if (!state.job) {
                    return;
                }
                if (closeDialogFn) {
                    return;
                }
                closeDialogFn = dialog.add(
                    BatchEditProgressDialog,
                    {
                        getJob: () => state.job,
                        onCancel: () => service.cancelJob(),
                    },
                    {
                        onClose: () => {
                            closeDialogFn = null;
                        },
                    }
                );
            },
            hideDialog() {
                if (closeDialogFn) {
                    closeDialogFn();
                    closeDialogFn = null;
                }
            },
            async cancelJob() {
                if (!state.job) {
                    return;
                }
                try {
                    await rpc("/andykanoz_gemini_integration_auto_edit/cancel_job", {
                        job_id: state.job.job_id,
                    });
                } catch (e) {
                    notification.add(_t("Failed to cancel batch job."), {
                        type: "danger",
                    });
                    console.error(e);
                }
            },
        };
        return service;
    },
};

registry.category("services").add("batchEditService", batchEditService);

// Client action used by the wizard's action_start return value
registry
    .category("actions")
    .add("andykanoz_gemini_integration_auto_edit.open_progress_dialog", (env, action) => {
        env.services.batchEditService.openDialog();
        return { type: "ir.actions.act_window_close" };
    });
