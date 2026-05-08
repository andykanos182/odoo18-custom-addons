/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/*
 * Cross-platform BarcodeDetector helper.
 *
 * Strategy:
 *   1. Native BarcodeDetector API  — Chrome 83+, Edge 83+, Safari 17.2+ (iOS 17.2+)
 *   2. Polyfill via barcode-detector npm package (CDN) — older iOS, Firefox, etc.
 *   3. If both fail → camera scanning unavailable, hardware scanner + manual input still work.
 *
 * The polyfill exposes the same window.BarcodeDetector API using ZXing-WASM internally.
 */
let _polyfillLoaded = false;
let _polyfillFailed = false;

async function ensureBarcodeDetector() {
    // Already available natively
    if (typeof window.BarcodeDetector !== "undefined") {
        return true;
    }
    // Already tried and failed
    if (_polyfillFailed) return false;
    // Already loaded polyfill
    if (_polyfillLoaded) {
        return typeof window.BarcodeDetector !== "undefined";
    }

    // Load polyfill from CDN
    return new Promise((resolve) => {
        const script = document.createElement("script");
        script.src = "https://fastly.jsdelivr.net/npm/barcode-detector@2/dist/es/polyfill.min.js";
        script.onload = () => {
            _polyfillLoaded = true;
            resolve(typeof window.BarcodeDetector !== "undefined");
        };
        script.onerror = () => {
            _polyfillFailed = true;
            console.warn("BarcodeDetector polyfill failed to load from CDN.");
            resolve(false);
        };
        document.head.appendChild(script);
    });
}


export class BarcodeReceivingAction extends Component {
    static template = "andykanoz_barcode_receiving.BarcodeReceivingAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.inputRef = useRef("barcodeInput");
        this.videoRef = useRef("cameraVideo");

        this.state = useState({
            picking: null,
            pending: [],
            received: [],
            loading: true,
            scanMessage: "",
            scanMessageType: "",
            lastScannedId: null,
            // Camera states
            showCamera: false,
            cameraError: null,
            cameraLoading: false,
            torchSupported: false,
            torchOn: false,
        });

        this.pickingId = this.props.action.params?.picking_id
            || this.props.action.context?.picking_id;

        // Camera internals
        this._cameraStream = null;
        this._cameraTrack = null;
        this._scanInterval = null;
        this._detector = null;

        // Listen to hardware barcode scanner via barcode service
        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));

        // Load audio
        const fileExtension = new Audio().canPlayType("audio/ogg") ? "ogg" : "mp3";
        this.sounds = {
            success: new Audio(url(`/mail/static/src/audio/ting.${fileExtension}`)),
            error: new Audio(url(`/barcodes/static/src/audio/error.${fileExtension}`)),
        };

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.focusInput();
        });

        onWillUnmount(() => {
            this._stopCamera();
        });
    }

    // ─── DATA LOADING ───

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "stock.picking",
                "get_barcode_receiving_data",
                [this.pickingId]
            );
            this.state.picking = {
                id: data.picking_id,
                name: data.picking_name,
                partner_name: data.partner_name,
                origin: data.origin,
                state: data.state,
            };
            this.state.pending = data.pending;
            this.state.received = data.received;
        } catch (e) {
            this.notification.add(_t("Failed to load receiving data."), { type: "danger" });
        }
        this.state.loading = false;
    }

    focusInput() {
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
    }

    playSound(type) {
        const sound = this.sounds[type];
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(() => {});
        }
    }

    // ─── BARCODE PROCESSING ───

    async onBarcodeScanned(barcode) {
        await this.processBarcode(barcode);
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            const val = ev.target.value.trim();
            if (val) {
                this.processBarcode(val);
                ev.target.value = "";
            }
        }
    }

    async processBarcode(barcode) {
        this.state.scanMessage = "";
        this.state.lastScannedId = null;

        try {
            const result = await this.orm.call(
                "stock.picking",
                "process_barcode_scan",
                [this.pickingId, barcode]
            );

            if (result.success) {
                this.playSound("success");
                this.state.scanMessage = _t("Received: %s (Qty: %s)", result.product_name, result.demand);
                this.state.scanMessageType = "success";
                this.state.lastScannedId = result.move_id;
                await this.loadData();
            } else {
                this.playSound("error");
                this.state.scanMessage = result.error;
                this.state.scanMessageType = "error";
            }
        } catch (e) {
            this.playSound("error");
            this.state.scanMessage = _t("Error processing barcode.");
            this.state.scanMessageType = "error";
        }

        // Clear input field
        if (this.inputRef.el) {
            this.inputRef.el.value = "";
            this.inputRef.el.focus();
        }
    }

    // ─── CAMERA SCANNER ───

    async openCamera() {
        this.state.showCamera = true;
        this.state.cameraError = null;
        this.state.cameraLoading = true;

        try {
            // Ensure BarcodeDetector is available (native or polyfill)
            const available = await ensureBarcodeDetector();
            if (!available) {
                this.state.cameraLoading = false;
                this.state.cameraError = _t(
                    "Camera barcode scanning is not supported on this browser. " +
                    "Please use a hardware scanner or type the barcode manually."
                );
                return;
            }

            this._detector = new window.BarcodeDetector({
                formats: ["ean_13", "ean_8", "code_128", "code_39", "upc_a", "upc_e", "qr_code"],
            });

            // Request camera access — 'environment' = back camera on mobile
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: "environment" },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });

            this.state.cameraLoading = false;

            // Wait for OWL to render the video element, then bind stream
            await new Promise((r) => setTimeout(r, 150));
            if (this.videoRef.el && this._cameraStream) {
                this.videoRef.el.srcObject = this._cameraStream;
                this._cameraTrack = this._cameraStream.getVideoTracks()[0];
                this._checkTorch();
                // Start scanning loop
                this._scanInterval = setInterval(() => this._scanFrame(), 350);
            }
        } catch (e) {
            this.state.cameraLoading = false;
            if (e.name === "NotAllowedError") {
                this.state.cameraError = _t("Camera access denied. Please allow camera permissions in your browser settings.");
            } else if (e.name === "NotFoundError" || e.name === "DevicesNotFoundError") {
                this.state.cameraError = _t("No camera found on this device.");
            } else if (e.name === "NotReadableError") {
                this.state.cameraError = _t("Camera is in use by another application.");
            } else {
                this.state.cameraError = _t("Camera error: ") + e.message;
            }
        }
    }

    async _scanFrame() {
        if (!this._detector || !this.videoRef.el) return;
        if (this.videoRef.el.readyState < 2) return;

        try {
            const codes = await this._detector.detect(this.videoRef.el);
            if (codes && codes.length > 0) {
                const barcode = codes[0].rawValue;
                if (barcode) {
                    // Found a barcode — close camera and process
                    this.closeCamera();
                    await this.processBarcode(barcode);
                }
            }
        } catch (e) {
            // Detection error on this frame, continue scanning
        }
    }

    _checkTorch() {
        if (this._cameraTrack && typeof this._cameraTrack.getCapabilities === "function") {
            try {
                const caps = this._cameraTrack.getCapabilities();
                if (caps && caps.torch) {
                    this.state.torchSupported = true;
                }
            } catch (e) {
                // getCapabilities not available on some iOS versions
            }
        }
    }

    async toggleTorch() {
        if (!this._cameraTrack || !this.state.torchSupported) return;
        const newState = !this.state.torchOn;
        try {
            await this._cameraTrack.applyConstraints({ advanced: [{ torch: newState }] });
            this.state.torchOn = newState;
        } catch (e) {}
    }

    closeCamera() {
        this._stopCamera();
        this.state.showCamera = false;
        this.state.cameraError = null;
        this.state.cameraLoading = false;
        this.state.torchSupported = false;
        this.state.torchOn = false;
        setTimeout(() => this.focusInput(), 100);
    }

    _stopCamera() {
        if (this._scanInterval) {
            clearInterval(this._scanInterval);
            this._scanInterval = null;
        }
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach((t) => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this._detector = null;
    }

    // ─── ACTIONS ───

    async onValidate() {
        try {
            const result = await this.orm.call(
                "stock.picking",
                "action_validate_from_barcode",
                [this.pickingId]
            );
            if (result && typeof result === "object" && result.type) {
                this.actionService.doAction(result);
            } else {
                this.notification.add(_t("Receipt validated successfully!"), { type: "success" });
                this.onBack();
            }
        } catch (e) {
            this.notification.add(
                e.data?.message || _t("Validation failed."),
                { type: "danger" }
            );
        }
    }

    onBack() {
        this._stopCamera();
        this.actionService.restore();
    }

    get progress() {
        const total = this.state.pending.length + this.state.received.length;
        if (total === 0) return 0;
        return Math.round((this.state.received.length / total) * 100);
    }

    get allReceived() {
        return this.state.pending.length === 0 && this.state.received.length > 0;
    }
}

registry.category("actions").add("andykanoz_barcode_receiving", BarcodeReceivingAction);
