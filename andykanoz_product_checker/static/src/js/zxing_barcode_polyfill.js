/** @odoo-module **/
/**
 * BarcodeDetector polyfill for iOS Safari & Chrome.
 *
 * Native BarcodeDetector API is available on Chrome Android and Edge,
 * but NOT on iOS Safari or Chrome iOS (which uses WebKit engine).
 *
 * This module loads the `barcode-detector` polyfill from CDN on demand.
 * The polyfill uses ZXing WASM internally and implements the standard
 * BarcodeDetector API, so existing code works unchanged.
 *
 * Usage in other modules:
 *   import { ensureBarcodeDetector } from "./zxing_barcode_polyfill";
 *   await ensureBarcodeDetector(); // loads polyfill if needed
 *   const detector = new window.BarcodeDetector({formats: [...]});
 */

let _polyfillLoaded = false;
let _loadingPromise = null;

/**
 * CDN URLs to try, in order. We use multiple CDNs for reliability.
 * The `barcode-detector` npm package by Nicolo Ribaudo is the standard
 * polyfill for the BarcodeDetector API.
 */
const CDN_URLS = [
    "https://fastly.jsdelivr.net/npm/barcode-detector@2/dist/es/side-effects.min.js",
    "https://cdn.jsdelivr.net/npm/barcode-detector@2/dist/es/side-effects.min.js",
    "https://unpkg.com/barcode-detector@2/dist/es/side-effects.min.js",
];

/**
 * Try loading the polyfill via dynamic import() from CDN.
 * The side-effects build auto-registers window.BarcodeDetector.
 * Safari iOS supports dynamic import() from external URLs natively.
 */
async function _tryLoadFromCDN(url) {
    await import(/* @vite-ignore */ url);
}

/**
 * Load the BarcodeDetector polyfill. Tries multiple CDN sources.
 */
async function _loadPolyfill() {
    if (_polyfillLoaded) return;
    if (_loadingPromise) return _loadingPromise;

    _loadingPromise = (async () => {
        for (const url of CDN_URLS) {
            try {
                await _tryLoadFromCDN(url);
                if (typeof window.BarcodeDetector !== "undefined") {
                    _polyfillLoaded = true;
                    console.log("[BarcodePolyfill] Loaded from:", url);
                    return;
                }
            } catch (e) {
                console.warn("[BarcodePolyfill] Failed to load from:", url, e.message || e);
            }
        }

        // All CDN attempts failed — register a no-op fallback so the camera
        // at least opens (user can still see the viewfinder, just no decoding).
        // This is better than showing "not supported" error.
        if (typeof window.BarcodeDetector === "undefined") {
            window.BarcodeDetector = class NoOpBarcodeDetector {
                constructor() {}
                static async getSupportedFormats() { return []; }
                async detect() { return []; }
            };
            _polyfillLoaded = true;
            console.warn(
                "[BarcodePolyfill] CDN unreachable — barcode camera scanning unavailable. " +
                "Use manual barcode input instead."
            );
        }
    })();

    return _loadingPromise;
}

/**
 * Ensure BarcodeDetector is available before using it.
 * On browsers with native support (Chrome Android), returns immediately.
 * On iOS Safari/Chrome, loads the polyfill from CDN.
 *
 * @returns {Promise<boolean>} true if BarcodeDetector is available
 */
export async function ensureBarcodeDetector() {
    if (typeof window.BarcodeDetector !== "undefined") {
        return true;
    }
    await _loadPolyfill();
    return typeof window.BarcodeDetector !== "undefined";
}
