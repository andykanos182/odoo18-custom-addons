/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { Component, useState, useRef, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class BarcodeScannerCharField extends CharField {
    static template = "andykanoz_scaner_barcode_inventory.BarcodeScannerCharField";

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.videoRef = useRef("cameraVideo");
        this.state = useState({
            showScanner: false,
            cameraError: null,
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

    async openScanner() {
        this.state.showScanner = true;
        this.state.cameraError = null;
        
        if (typeof window.BarcodeDetector === "undefined") {
            this.state.cameraError = _t("Barcode Detector API not supported. Use Chrome Android or Edge.");
            return;
        }

        try {
            this._barcodeDetector = new window.BarcodeDetector({
                formats: ["ean_13", "ean_8", "code_128", "code_39", "upc_a", "upc_e", "qr_code"],
            });

            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false,
            });

            // Brief delay to ensure video element is rendered by OWL
            setTimeout(() => {
                if (this.videoRef.el) {
                    this.videoRef.el.srcObject = this._cameraStream;
                    this._cameraTrack = this._cameraStream.getVideoTracks()[0];
                    this._checkTorch();
                    this._scanLoopHandle = setInterval(() => this._scanFrame(), 300);
                }
            }, 100);
        } catch (e) {
            this.state.cameraError = _t("Camera access denied or failed: ") + e.message;
        }
    }

    async _scanFrame() {
        if (!this._barcodeDetector || !this.videoRef.el || this.videoRef.el.readyState < 2) return;
        try {
            const codes = await this._barcodeDetector.detect(this.videoRef.el);
            if (codes && codes.length > 0) {
                const barcode = codes[0].rawValue;
                if (barcode) {
                    // Fill the field and close
                    this.props.record.update({ [this.props.name]: barcode });
                    this.closeScanner();
                    this.notification.add(_t("Barcode Scanned: ") + barcode, { type: "success" });
                }
            }
        } catch (e) {}
    }

    _checkTorch() {
        if (this._cameraTrack && typeof this._cameraTrack.getCapabilities === "function") {
            const caps = this._cameraTrack.getCapabilities();
            if (caps && caps.torch) {
                this.state.torchSupported = true;
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

    closeScanner() {
        this._stopCamera();
        this.state.showScanner = false;
    }

    _stopCamera() {
        if (this._scanLoopHandle) clearInterval(this._scanLoopHandle);
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach(t => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this._scanLoopHandle = null;
    }
}

export const barcodeScannerCharField = {
    ...charField,
    component: BarcodeScannerCharField,
};

registry.category("fields").add("andykanoz_barcode_scanner", barcodeScannerCharField);
