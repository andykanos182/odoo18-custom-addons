/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * BarcodeScanner — full-screen camera overlay that detects barcodes
 * via the native BarcodeDetector API and emits the decoded value.
 *
 * Pattern reference: andykanoz_quick_purchase. The scanner runs as a
 * modal-over-modal on top of ProductPicker so the search input stays
 * available as a fallback when the camera fails or the user cancels.
 *
 * Browser support:
 *   - Chrome Android 83+: native BarcodeDetector ✅
 *   - Chrome Desktop: requires chrome://flags/#enable-experimental-web-platform-features
 *   - Safari iOS: NOT supported (uses Vision framework via WKWebView,
 *     not exposed to web). On iOS we hide the scan button entirely.
 *   - Firefox: NOT supported (no BarcodeDetector at all).
 *
 * Props:
 *   onDetect(text) — called with decoded barcode/QR string. The
 *                    component does NOT auto-close after detection;
 *                    the parent decides whether to close based on the
 *                    detection result (e.g. close on exact-match SKU,
 *                    keep open on ambiguous result).
 *   onClose() — called when user taps the X button or hardware back.
 *
 * Lifecycle:
 *   - onMounted: requestUserMedia, set up BarcodeDetector, start
 *                animation-frame polling loop
 *   - onWillUnmount: stop video stream tracks (releases camera) and
 *                    cancel any pending requestAnimationFrame
 *
 * Performance:
 *   - Uses requestAnimationFrame instead of setInterval so detection
 *     pauses when the tab is backgrounded.
 *   - Throttles to ~5 detections/sec via _lastDetectAt timestamp;
 *     full-rate detection burns battery without improving UX.
 */
export class BarcodeScanner extends Component {
    static template = "andykanoz_purchase_mobile.BarcodeScanner";
    static props = {
        onDetect: { type: Function },
        onClose: { type: Function },
    };

    setup() {
        this.state = useState({
            error: null,
            torch: false,
            torchAvailable: false,
            scanning: true,
        });
        this._videoRef = useRef("video");
        this._stream = null;
        this._track = null;
        this._detector = null;
        this._raf = null;
        this._lastDetectAt = 0;
        this._lastEmitted = null;

        onMounted(() => this._start());
        onWillUnmount(() => this._stop());
    }

    static isSupported() {
        return typeof window !== "undefined" && "BarcodeDetector" in window;
    }

    async _start() {
        if (!BarcodeScanner.isSupported()) {
            this.state.error = "Browser tidak mendukung scan barcode. Pakai Chrome Android terbaru.";
            this.state.scanning = false;
            return;
        }

        try {
            // Prefer back camera ('environment'). Some devices ignore
            // the constraint silently and return the front camera —
            // we accept that rather than fail.
            this._stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false,
            });
        } catch (e) {
            this.state.error = "Tidak bisa akses kamera. Cek izin di browser.";
            this.state.scanning = false;
            return;
        }

        const video = this._videoRef.el;
        if (!video) return;
        video.srcObject = this._stream;
        try {
            await video.play();
        } catch (e) {
            // Autoplay policies — should never reject after user gesture
            // that opened the modal, but be defensive.
            this.state.error = "Gagal memulai video stream.";
            this.state.scanning = false;
            return;
        }

        // Detect torch capability for the current track.
        this._track = this._stream.getVideoTracks()[0];
        if (this._track && typeof this._track.getCapabilities === "function") {
            const caps = this._track.getCapabilities();
            this.state.torchAvailable = !!caps.torch;
        }

        // Initialize detector. Requesting all common formats covers
        // what shows up on F&B inventory: EAN-13 (retail barcodes),
        // CODE-128 (warehouse/shipping), CODE-39 (legacy SKUs),
        // QR (modern internal codes).
        try {
            this._detector = new window.BarcodeDetector({
                formats: ["ean_13", "ean_8", "code_128", "code_39", "qr_code", "upc_a", "upc_e"],
            });
        } catch (e) {
            // Fallback: let the detector pick supported formats itself
            this._detector = new window.BarcodeDetector();
        }

        // Begin polling.
        this._raf = requestAnimationFrame(() => this._tick());
    }

    async _tick() {
        if (!this.state.scanning) return;
        const video = this._videoRef.el;
        if (!video || !this._detector) {
            this._raf = requestAnimationFrame(() => this._tick());
            return;
        }

        // Throttle to ~5/sec.
        const now = Date.now();
        if (now - this._lastDetectAt < 200) {
            this._raf = requestAnimationFrame(() => this._tick());
            return;
        }
        this._lastDetectAt = now;

        try {
            const results = await this._detector.detect(video);
            if (results && results.length > 0) {
                const text = results[0].rawValue;
                // Suppress duplicate emissions of the same code in
                // rapid succession — the parent might keep us mounted
                // even after a successful match (e.g. ambiguous query)
                // and we don't want to spam onDetect.
                if (text && text !== this._lastEmitted) {
                    this._lastEmitted = text;
                    this.props.onDetect(text);
                }
            }
        } catch (e) {
            // detect() can throw transiently (frame not ready). Just
            // skip this tick and continue.
        }

        this._raf = requestAnimationFrame(() => this._tick());
    }

    _stop() {
        this.state.scanning = false;
        if (this._raf) {
            cancelAnimationFrame(this._raf);
            this._raf = null;
        }
        if (this._stream) {
            for (const t of this._stream.getTracks()) {
                try { t.stop(); } catch (e) { /* ignore */ }
            }
            this._stream = null;
        }
        this._track = null;
        this._detector = null;
    }

    async toggleTorch() {
        if (!this._track || !this.state.torchAvailable) return;
        const next = !this.state.torch;
        try {
            await this._track.applyConstraints({
                advanced: [{ torch: next }],
            });
            this.state.torch = next;
        } catch (e) {
            // Some devices report torch as supported but reject the
            // constraint. Hide the button on persistent failure so the
            // user doesn't keep tapping a non-functional control.
            this.state.torchAvailable = false;
        }
    }

    onCloseClick() {
        this.props.onClose();
    }
}
