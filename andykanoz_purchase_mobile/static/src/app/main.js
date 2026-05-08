/** @odoo-module **/

import { App, whenReady } from "@odoo/owl";
import { templates } from "@web/core/templates";
import { PurchaseMobileApp } from "./app";

/**
 * Mount the OWL app as soon as the DOM is ready, but only on the
 * Purchase Mobile page. Because we inject into `web.assets_frontend`,
 * this script loads on every frontend page — so we guard by looking
 * for our specific mount-point element before doing any work.
 */
(async function () {
    await whenReady();

    const rootEl = document.getElementById("andykanoz-purchase-mobile-app");
    if (!rootEl) {
        // Not on our page — stay silent.
        return;
    }

    // Clear the server-rendered "Loading app…" placeholder before mount.
    rootEl.innerHTML = "";

    try {
        const app = new App(PurchaseMobileApp, {
            templates,
            name: "Purchase Mobile",
            dev: true,
            translateFn: (s) => s,
        });
        await app.mount(rootEl);
    } catch (err) {
        // Fallback UI so the user sees what went wrong instead of a
        // blank page when OWL bootstrap fails.
        rootEl.innerHTML = `
            <div style="padding:24px;color:#A32D2D;font-family:sans-serif;">
                <strong>App failed to start.</strong>
                <pre style="white-space:pre-wrap;font-size:12px;margin-top:8px;">${
                    err && err.stack ? err.stack : String(err)
                }</pre>
            </div>
        `;
        // Re-throw so it also shows up in the console.
        throw err;
    }
})();
