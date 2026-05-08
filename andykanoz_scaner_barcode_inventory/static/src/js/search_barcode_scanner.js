/** @odoo-module **/

import { Component, useState, useRef, onWillUnmount, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class BarcodeScannerMobileButton extends Component {
    static template = "andykanoz_scaner_barcode_inventory.BarcodeScannerMobileButton";

    setup() {
        this.notification = useService("notification");
        // router service may not be present in all client contexts; try/catch to be safe
        try {
            this.router = useService("router");
        } catch (e) {
            this.router = null;
        }

        this.videoRef = useRef("searchCameraVideo");
        this.state = useState({
            showScanner: false,
            cameraError: null,
            torchSupported: false,
            torchOn: false,
            isMobile: this._isMobileOrTablet(),
            // allowedPage true only when current route/model is product.template/product.product
            allowedPage: false,
        });

        this._cameraStream = null;
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this._scanLoopHandle = null;

        this._onResize = () => {
            this.state.isMobile = this._isMobileOrTablet();
            this._updateAllowedPage();
        };
        window.addEventListener("resize", this._onResize);

        // Determine whether the FAB should be visible on the current page.
        // Prefer the router service (robust); fallback to parsing location.href and deep DOM cues.
        this._updateAllowedPage = () => {
            let allowed = false;
            try {
                let model = null;
                if (this.router && this.router.current) {
                    if (this.router.current.hash && this.router.current.hash.model) {
                        model = this.router.current.hash.model;
                    } else if (this.router.current.search && this.router.current.search.model) {
                        model = this.router.current.search.model;
                    }
                }

                if (model) {
                    if (model === "product.template" || model === "product.product") {
                        allowed = true;
                    }
                } else {
                    const url = window.location.href || "";
                    if (url.includes("model=product.template") || url.includes("model=product.product")) {
                        allowed = true;
                    }
                    if (!allowed) {
                        // DOM-based fallback: look for typical product form/search/view markers
                        const els = document.querySelectorAll('.o_view_controller, form[data-model], [data-model], .o_breadcrumb, .breadcrumb');
                        for (let el of els) {
                            const dm = el.getAttribute('data-model') || el.className || el.textContent || '';
                            if (dm.includes('product.template') || dm.includes('product.product') || dm.toLowerCase().includes('product')) {
                                allowed = true;
                                break;
                            }
                        }
                    }
                }
            } catch (e) {
                allowed = false;
            }
            this.state.allowedPage = allowed;
        };

        // Initial evaluation
        this._updateAllowedPage();

        // Use MutationObserver as the ultimate fallback for SPA navigations
        this._observer = new MutationObserver(() => {
            this._updateAllowedPage();
        });
        this._observer.observe(document.body, { childList: true, subtree: true });

        // Try to subscribe to router events; if not possible, use hashchange fallback.
        if (this.router && typeof this.router.on === "function" && typeof this.router.off === "function") {
            this._routerHandler = () => this._updateAllowedPage();
            try {
                this.router.on("change", this._routerHandler);
            } catch (e) {
                this._hashHandler = () => this._updateAllowedPage();
                window.addEventListener("hashchange", this._hashHandler);
            }
        } else {
            this._hashHandler = () => this._updateAllowedPage();
            window.addEventListener("hashchange", this._hashHandler);
        }

        onWillUnmount(() => {
            if (this._observer) {
                this._observer.disconnect();
            }
            this._stopCamera();
            window.removeEventListener("resize", this._onResize);
            if (this.router && typeof this.router.off === "function" && this._routerHandler) {
                try {
                    this.router.off("change", this._routerHandler);
                } catch (e) { }
            }
            if (this._hashHandler) {
                window.removeEventListener("hashchange", this._hashHandler);
            }
        });
    }

    /**
     * Detect touch-primary devices (phones, tablets).
     * pointer:coarse = finger as primary input (not mouse).
     * Fallback to maxTouchPoints for older browsers.
     */
    _isMobileOrTablet() {
        if (window.matchMedia("(pointer: coarse)").matches) {
            return true;
        }
        return navigator.maxTouchPoints > 0 && window.innerWidth <= 1366;
    }

    async openScanner() {
        this.state.showScanner = true;
        this.state.cameraError = null;

        if (typeof window.BarcodeDetector === "undefined") {
            this.state.cameraError = _t(
                "Barcode Detector API not supported. Use Chrome Android or Edge."
            );
            return;
        }

        try {
            this._barcodeDetector = new window.BarcodeDetector({
                formats: [
                    "ean_13", "ean_8", "code_128", "code_39",
                    "upc_a", "upc_e", "qr_code",
                ],
            });

            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } },
                audio: false,
            });

            setTimeout(() => {
                if (this.videoRef.el) {
                    this.videoRef.el.srcObject = this._cameraStream;
                    this._cameraTrack = this._cameraStream.getVideoTracks()[0];
                    this._checkTorch();
                    this._scanLoopHandle = setInterval(() => this._scanFrame(), 300);
                }
            }, 100);
        } catch (e) {
            this.state.cameraError =
                _t("Camera access denied or failed: ") + e.message;
        }
    }

    async _scanFrame() {
        if (
            !this._barcodeDetector ||
            !this.videoRef.el ||
            this.videoRef.el.readyState < 2
        ) {
            return;
        }
        try {
            const codes = await this._barcodeDetector.detect(this.videoRef.el);
            if (codes && codes.length > 0) {
                const barcode = codes[0].rawValue;
                if (barcode) {
                    this.closeScanner();
                    this._fillSearchAndTrigger(barcode);
                }
            }
        } catch (e) {
            // silently ignore frame errors
        }
    }

    /**
     * Find the Odoo search input on the page, fill it with the scanned
     * barcode, and trigger the search (Enter key).
     */
    _fillSearchAndTrigger(barcode) {
        const searchInput = document.querySelector(".o_searchview_input");
        if (!searchInput) {
            this.notification.add(
                _t("Barcode: ") + barcode + " — " + _t("No search bar found on this page."),
                { type: "warning" }
            );
            return;
        }

        // Focus the input first
        searchInput.focus();

        // Set value using native setter so OWL picks it up
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype,
            "value"
        ).set;
        nativeSetter.call(searchInput, barcode);

        // Dispatch input event so OWL's t-on-input handler reads the new value
        searchInput.dispatchEvent(
            new InputEvent("input", {
                bubbles: true,
                data: barcode,
                inputType: "insertText",
            })
        );

        // Short delay, then press Enter to trigger the actual search
        setTimeout(() => {
            searchInput.dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "Enter",
                    code: "Enter",
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                })
            );
            this.notification.add(
                _t("Barcode Scanned: ") + barcode,
                { type: "success" }
            );
        }, 200);
    }

    _checkTorch() {
        if (
            this._cameraTrack &&
            typeof this._cameraTrack.getCapabilities === "function"
        ) {
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
            await this._cameraTrack.applyConstraints({
                advanced: [{ torch: newState }],
            });
            this.state.torchOn = newState;
        } catch (e) {
            // silently ignore torch errors
        }
    }

    closeScanner() {
        this._stopCamera();
        this.state.showScanner = false;
    }

    _stopCamera() {
        if (this._scanLoopHandle) {
            clearInterval(this._scanLoopHandle);
        }
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach((t) => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this._scanLoopHandle = null;
    }
}

registry.category("main_components").add("BarcodeScannerMobileButton", {
    Component: BarcodeScannerMobileButton,
});
