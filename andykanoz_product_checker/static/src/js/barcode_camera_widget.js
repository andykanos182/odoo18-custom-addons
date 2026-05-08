/** @odoo-module **/

import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { useState, useRef, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ensureBarcodeDetector } from "./zxing_barcode_polyfill";

export class BarcodeCameraField extends CharField {
    static template = "andykanoz_product_checker.BarcodeCameraField";

    setup() {
        super.setup();
        this.cameraVideoRef = useRef("cameraVideo");
        this.cameraState = useState({
            showModal: false,
            cameraFacing: "environment",
            cameraError: null,
            lastDetected: null,
            torchSupported: false,
            torchOn: false,
        });

        this._cameraStream = null;
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this._scanLoopHandle = null;

        onWillUnmount(() => {
            this._stopCamera();
        });
    }

    // ============ CAMERA ============

    async openCamera() {
        this.cameraState.cameraError = null;
        this.cameraState.lastDetected = null;
        this.cameraState.torchSupported = false;
        this.cameraState.torchOn = false;
        this.cameraState.showModal = true;

        // Load BarcodeDetector polyfill for iOS Safari/Chrome if needed
        const hasBarcodeDetector = await ensureBarcodeDetector();
        if (!hasBarcodeDetector) {
            this.cameraState.cameraError = _t(
                "Your browser does not support the Barcode Detector API. " +
                "Please use Chrome on Android, or type the barcode manually."
            );
            return;
        }

        try {
            this._barcodeDetector = new window.BarcodeDetector({
                formats: [
                    "ean_13", "ean_8", "code_128", "code_39",
                    "upc_a", "upc_e", "itf", "qr_code", "codabar",
                ],
            });
        } catch (e) {
            this.cameraState.cameraError = _t("Failed to initialize barcode detector: ") + e.message;
            return;
        }

        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: this.cameraState.cameraFacing },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });
        } catch (e) {
            this.cameraState.cameraError = _t(
                "Cannot access camera: " + (e.message || e) +
                ". Make sure you have granted camera permission."
            );
            return;
        }

        setTimeout(() => {
            if (!this.cameraVideoRef.el) {
                this.cameraState.cameraError = _t("Video element not ready.");
                this._stopCamera();
                return;
            }

            const videoEl = this.cameraVideoRef.el;
            videoEl.srcObject = this._cameraStream;
            this._cameraTrack = this._cameraStream.getVideoTracks()[0];

            const onPlaying = () => {
                videoEl.removeEventListener("playing", onPlaying);
                this._detectTorch();
            };
            videoEl.addEventListener("playing", onPlaying);

            setTimeout(() => {
                videoEl.removeEventListener("playing", onPlaying);
                if (!this.cameraState.torchSupported && this._cameraTrack) {
                    this._detectTorch();
                }
            }, 3000);

            this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
        }, 150);
    }

    _detectTorch() {
        let attempts = 0;
        const check = () => {
            if (this._cameraTrack) {
                let hasTorch = false;
                if (typeof this._cameraTrack.getCapabilities === "function") {
                    const caps = this._cameraTrack.getCapabilities();
                    if (caps && caps.torch) hasTorch = true;
                }
                if (!hasTorch && typeof this._cameraTrack.getSettings === "function") {
                    const s = this._cameraTrack.getSettings();
                    if (s && "torch" in s) hasTorch = true;
                }
                if (hasTorch) {
                    this.cameraState.torchSupported = true;
                    return;
                }
            }
            if (++attempts < 20 && this.cameraState.showModal) {
                setTimeout(check, 500);
            }
        };
        check();
    }

    async _scanFrame() {
        if (!this._barcodeDetector || !this.cameraVideoRef.el) return;
        const video = this.cameraVideoRef.el;
        if (video.readyState < 2) return;
        try {
            const codes = await this._barcodeDetector.detect(video);
            if (codes && codes.length > 0 && codes[0].rawValue) {
                const value = codes[0].rawValue;
                this.cameraState.lastDetected = value;
                // Set the barcode field value on the record
                await this.props.record.update({ [this.props.name]: value });
                this.closeCamera();
            }
        } catch (_e) {
            // transient detection errors are ignored
        }
    }

    async toggleTorch() {
        if (!this._cameraTrack || !this.cameraState.torchSupported) return;
        const newState = !this.cameraState.torchOn;
        try {
            await this._cameraTrack.applyConstraints({ advanced: [{ torch: newState }] });
            this.cameraState.torchOn = newState;
        } catch (_e) { /* ignore */ }
    }

    async switchCamera() {
        this.cameraState.cameraFacing =
            this.cameraState.cameraFacing === "environment" ? "user" : "environment";

        // Stop current stream but keep modal open
        if (this._scanLoopHandle) {
            clearInterval(this._scanLoopHandle);
            this._scanLoopHandle = null;
        }
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach(t => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this.cameraState.torchOn = false;
        this.cameraState.torchSupported = false;

        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: this.cameraState.cameraFacing },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });
        } catch (e) {
            this.cameraState.cameraError = _t("Cannot switch camera: ") + (e.message || e);
            return;
        }

        if (this.cameraVideoRef.el) {
            const videoEl = this.cameraVideoRef.el;
            videoEl.srcObject = this._cameraStream;
            this._cameraTrack = this._cameraStream.getVideoTracks()[0];

            const onPlaying = () => {
                videoEl.removeEventListener("playing", onPlaying);
                this._detectTorch();
            };
            videoEl.addEventListener("playing", onPlaying);
            setTimeout(() => {
                videoEl.removeEventListener("playing", onPlaying);
                if (!this.cameraState.torchSupported && this._cameraTrack) {
                    this._detectTorch();
                }
            }, 3000);

            this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
        }
    }

    closeCamera() {
        this._stopCamera();
        this.cameraState.showModal = false;
    }

    _stopCamera() {
        if (this._scanLoopHandle) {
            clearInterval(this._scanLoopHandle);
            this._scanLoopHandle = null;
        }
        if (this._cameraTrack && this.cameraState.torchOn) {
            try {
                this._cameraTrack.applyConstraints({ advanced: [{ torch: false }] });
            } catch (_e) { /* ignore */ }
        }
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach(t => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this.cameraState.torchOn = false;
        this.cameraState.torchSupported = false;
    }
}

export const barcodeCameraField = {
    ...charField,
    component: BarcodeCameraField,
};

registry.category("fields").add("barcode_camera", barcodeCameraField);
