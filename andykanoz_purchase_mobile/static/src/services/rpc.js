/** @odoo-module **/

/**
 * Minimal JSON-RPC wrapper for Odoo controllers declared with
 * type='json'. Sends the standard { jsonrpc, method, params }
 * envelope and unwraps the result (or throws on error).
 *
 * Deliberately dependency-free — we don't import from @web/core/network
 * because that pulls the whole ORM service / notification stack we don't
 * need here. Plain fetch keeps the bundle footprint small.
 *
 * Usage:
 *   import { jsonRpc } from "@andykanoz_purchase_mobile/services/rpc";
 *   const res = await jsonRpc("/andykanoz_purchase_mobile/api/vendors",
 *                             { query: "", limit: 10 });
 */
export async function jsonRpc(endpoint, params = {}) {
    let response;
    try {
        response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: params,
                id: Math.floor(Math.random() * 1e9),
            }),
        });
    } catch (err) {
        throw new Error(`Network error: ${err.message}`);
    }

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.error) {
        const msg =
            (data.error.data && data.error.data.message) ||
            data.error.message ||
            "Unknown JSON-RPC error";
        throw new Error(msg);
    }
    return data.result;
}
