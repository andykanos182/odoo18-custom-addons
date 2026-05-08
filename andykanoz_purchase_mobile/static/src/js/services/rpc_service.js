/** @odoo-module **/

/**
 * Minimal JSON-RPC client matching Odoo 18's JSON-RPC protocol.
 * Wraps fetch() with the proper envelope + error extraction so
 * components can just `await rpc(endpoint, params)` and get the
 * `result` payload directly.
 *
 * Throws Error with a readable message on:
 *   - Network failure
 *   - HTTP non-2xx
 *   - JSON-RPC error frame (data.error present)
 */
export async function rpc(endpoint, params = {}) {
    let response;
    try {
        response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: params,
            }),
            credentials: "same-origin",
        });
    } catch (e) {
        throw new Error("Network error: " + e.message);
    }
    if (!response.ok) {
        throw new Error("HTTP " + response.status + " " + response.statusText);
    }
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error("Invalid JSON response (session expired?)");
    }
    if (data.error) {
        const msg =
            (data.error.data && data.error.data.message) ||
            data.error.message ||
            "Unknown JSON-RPC error";
        throw new Error(msg);
    }
    return data.result;
}
