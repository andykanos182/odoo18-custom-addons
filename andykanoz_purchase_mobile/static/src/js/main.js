/** @odoo-module **/

import { App, whenReady } from "@odoo/owl";
import { makeEnv, startServices } from "@web/env";
import { getTemplate } from "@web/core/templates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PurchaseMobileApp } from "./purchase_mobile_app";

// ---------------------------------------------------------------------
// Side-effect: patch duplicate-key-tolerance into the registry
// categories that createPublicRoot (from @website) touches. Both need
// to be installed synchronously during module factory evaluation,
// before createPublicRoot fires via whenReady, so the race is already
// neutralized by the time it starts.
//
// Why per-category instance patches (not Registry.prototype):
//   Patching the prototype breaks Odoo startup — some internal .add()
//   calls legitimately rely on duplicates throwing. Per-instance
//   patches keep strict behavior everywhere else.
//
// Why both categories:
//   createPublicRoot's startServices registers into multiple
//   registries. "NotificationContainer" goes into main_components,
//   "web_tour.tour_enabled" goes into user_menuitems. Whichever one
//   throws first aborts the rest of createPublicRoot and triggers an
//   unhandled promise rejection, which cancels our whenReady callback.
//   Guarding both makes startServices succeed cleanly.
// ---------------------------------------------------------------------
function tolerantAddPatch(categoryKey) {
    const cat = registry.category(categoryKey);
    const originalAdd = cat.add.bind(cat);
    cat.add = function patchedAdd(key, value, options = {}) {
        try {
            return originalAdd(key, value, options);
        } catch (e) {
            if (/already exists|DuplicatedKey/i.test((e && e.message) || "")) {
                return cat;
            }
            throw e;
        }
    };
}
tolerantAddPatch("main_components");
tolerantAddPatch("user_menuitems");

/**
 * Mount bootstrap — matches the working version from the 12:02 PM
 * screenshot. Builds env with makeEnv + startServices, mounts via
 * OWL's App directly (not mountComponent from @web/env), and uses a
 * dataset guard for idempotency.
 */
whenReady(async () => {
    const rootEl = document.getElementById("app");
    if (!rootEl || rootEl.dataset.userLogin === undefined) {
        return;
    }
    if (rootEl.dataset.pmMounted === "1") {
        return;
    }
    rootEl.dataset.pmMounted = "1";

    const initialData = {
        userName: rootEl.dataset.userName || "",
        userLogin: rootEl.dataset.userLogin || "",
        phase: rootEl.dataset.phase || "",
        moduleVersion: rootEl.dataset.moduleVersion || "",
    };

    try {
        // Yield so createPublicRoot / publicRoot finishes its own
        // startServices() pass before we try to.
        await new Promise((r) => setTimeout(r, 0));

        const env = makeEnv();
        try {
            await startServices(env);
        } catch (e) {
            if (!/already exists|DuplicatedKey/i.test(e.message || "")) {
                throw e;
            }
            console.warn(
                "[purchase_mobile] startServices collision (ignored):",
                e.message
            );
        }

        const app = new App(PurchaseMobileApp, {
            env,
            getTemplate,
            translateFn: _t,
            dev: true,
            name: "PurchaseMobile",
            props: { initialData },
            warnIfNoStaticProps: true,
        });
        await app.mount(rootEl);

        document.getElementById("app-loading")?.remove();
        console.log("[purchase_mobile] OWL mounted");
    } catch (err) {
        console.error("[purchase_mobile] Mount failed:", err);
        rootEl.innerHTML =
            '<div style="padding:20px;font-family:sans-serif;color:#A32D2D;' +
            'background:#FCEBEB;border-radius:8px;margin:20px;">' +
            '<strong>OWL mount failed:</strong> ' +
            (err.message || String(err)) +
            '</div>';
    }
});
