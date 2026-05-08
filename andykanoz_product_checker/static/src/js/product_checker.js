/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { ensureBarcodeDetector } from "./zxing_barcode_polyfill";

export class ProductCheckerAction extends Component {
    static template = "andykanoz_product_checker.ProductCheckerPage";
    static props = ["*"];
    static components = { SelectMenu };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");

        this.barcodeInputRef = useRef("barcodeInput");
        this.cameraVideoRef = useRef("cameraVideo");
        this.galleryInputRef = useRef("galleryInput");
        this.cameraInputRef = useRef("cameraInput");
        this.costInputRef = useRef("costInput");
        this.stockInputRef = useRef("stockInput");

        this._audioCtx = null; // Web Audio API context

        // Camera state held outside reactive store (DOM/Stream objects)
        this._cameraStream = null;
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this._scanLoopHandle = null;
        this._lastScannedCode = null;
        this._lastScannedAt = 0;

        // Product List drawer — debounce timer for the search field
        this._productListDebounceTimer = null;

        let initialHistory = [];
        try {
            const storedHistory = window.localStorage.getItem("andykanoz_pc_history");
            if (storedHistory) {
                initialHistory = JSON.parse(storedHistory);
            }
        } catch (e) {
            console.warn("Could not load history from localStorage", e);
        }

        this.state = useState({
            barcode: "",
            loading: false,
            product: null,
            notFound: false,
            searchedCode: "",
            pricelists: [],
            selectedPricelistId: null,
            categories: [],
            publicCategories: [],
            history: initialHistory,
            sidebarOpen: false,
            // Print list state
            printList: [],
            autoAddToPrintList: false,
            printListPanelOpen: false,
            // Camera scanner state
            showCameraModal: false,
            cameraMode: "once",      // "once" or "continuous"
            cameraFacing: "environment", // "environment" (back) or "user" (front)
            cameraError: null,
            lastDetected: null,
            torchSupported: false,
            torchOn: false,
            scannedCount: 0,         // counter for continuous mode
            lastScanStatus: null,    // "success" | "duplicate" | null — for flash feedback
            lastScanMessage: null,   // feedback message for the toast
            // Quick create form state
            showCreateForm: false,
            showImageUpdateModal: false,
            // Image detail modal (opened when user taps the product image)
            imageDetailOpen: false,
            imageDetailUrl: null,
            showCostUpdateModal: false,
            showStockUpdateModal: false,
            editCostValue: 0,
            editStockValue: 0,
            createForm: {
                name: "",
                barcode: "",
                default_code: "",
                standard_price: 0,
                list_price: 0,
                categ_id: null,
                is_published: true,
                sale_ok: true,
                purchase_ok: true,
                available_in_pos: true,
                is_storable: true,
                public_categ_ids: [],
                pricelist_id: null,
                pricelist_price: 0,
            },
            // Category autocomplete (meta area)
            metaCategQuery: "",
            metaCategSuggestions: [],
            metaCategActiveSuggestion: -1,
            showMetaCategDropdown: false,
            metaCategShowQuickCreate: false,
            // Ecommerce category autocomplete (meta area, multi-select)
            pubCategQuery: "",
            pubCategSuggestions: [],
            pubCategActiveSuggestion: -1,
            showPubCategDropdown: false,
            // Product Tags (product_tag_ids) autocomplete
            productTags: [],
            tagQuery: "",
            tagSuggestions: [],
            tagActiveSuggestion: -1,
            showTagDropdown: false,
            // Product List drawer state (left-side panel)
            productListOpen: false,
            productListQuery: "",          // preserved across close/open cycles
            productListItems: [],
            productListTotal: 0,
            productListOffset: 0,
            productListLoading: false,
            productListInitialized: false, // true after first successful load
            // Custom Filter (Domain Selector dialog) state
            productListDomain: "[]",       // domain string; preserved across close/open
            productListFilterCount: 0,     // number of leaf rules; drives the badge
            // Saved favorites state
            savedFilters: [],              // list of {id, name, domain, query, is_default}
            activeSavedFilterId: null,     // currently selected favorite (null = none)
            favoritesDropdownOpen: false,
            saveFilterFormOpen: false,
            saveFilterName: "",
            saveFilterIsDefault: false,
            savedFiltersLoaded: false,     // true after first fetch; used to auto-apply default
            // Inline product-card toggles (Sales / Purchase / POS / Track / Published)
            savingOptionField: null,       // name of field currently saving (disables its switch)
            // Track Inventory error recovery
            showTrackInventoryErrorModal: false,
            trackInventoryErrorMessage: "",
            // Name-change undo helper (shows temporary Undo button)
            nameChangeUndoVisible: false,
        });

        // Temporary storage for undoing a title-case change
        this._lastNameBeforeTitleCase = null;
        this._nameChangeUndoTimer = null;

        onMounted(async () => {
            await this.loadConfig();
            this.focusInput();

            // Restore previous product if returning from full form
            const restoreCode = window.sessionStorage.getItem("pc_return_restore");
            if (restoreCode) {
                window.sessionStorage.removeItem("pc_return_restore");
                this.state.barcode = restoreCode;
                this.searchProduct(restoreCode);
            }

            // Global click handler to close the Favorites dropdown when
            // clicking outside of it. Stored on the instance so we can
            // remove it cleanly in onWillUnmount.
            this._onDocumentClick = (ev) => {
                if (!this.state.favoritesDropdownOpen) return;
                const wrap = ev.target && ev.target.closest && ev.target.closest('.o_pc_favorites_wrap');
                if (!wrap) {
                    this.state.favoritesDropdownOpen = false;
                }
            };
            document.addEventListener('click', this._onDocumentClick);
        });

        onWillUnmount(() => {
            this.stopCamera();
            if (this._onDocumentClick) {
                document.removeEventListener('click', this._onDocumentClick);
                this._onDocumentClick = null;
            }
            if (this._nameChangeUndoTimer) {
                clearTimeout(this._nameChangeUndoTimer);
                this._nameChangeUndoTimer = null;
            }
        });
    }


    get categoryChoices() {
        return (this.state.categories || []).map((c) => ({
            value: c.id,
            label: c.complete_name || c.name || "",
        }));
    }

    get pricelistChoices() {
        return (this.state.pricelists || []).map((p) => ({
            value: p.id,
            label: p.name || "",
        }));
    }

    get pricelistChoicesWithNone() {
        return [
            { value: null, label: _t("-- None --") },
            ...this.pricelistChoices,
        ];
    }

    get publicCategoryChoices() {
        return (this.state.publicCategories || []).map((p) => ({
            value: p.id,
            label: p.name || "",
        }));
    }

    get productTagChoices() {
        return (this.state.productTags || []).map((t) => ({
            value: t.id,
            label: t.name || "",
        }));
    }

    get productTagChoices() {
        return (this.state.productTags || []).map((t) => ({
            value: t.id,
            label: t.name || "",
        }));
    }


    async loadConfig() {
        try {
            const config = await this.orm.call(
                "product.template",
                "get_checker_config",
                []
            );
            this.state.pricelists = config.pricelists || [];
            this.state.selectedPricelistId = config.default_pricelist_id || null;
            this.state.categories = config.categories || [];
            this.state.publicCategories = config.public_categories || [];
            this.state.productTags = config.product_tags || [];
            this.state.printList = config.print_list || [];
        } catch (error) {
            this.notification.add(_t("Failed to load configuration"), {
                type: "danger",
            });
        }
    }

    /**
     * Undo the last title-case change (if within the temporary window).
     */
    async undoProductNameChange() {
        if (!this._lastNameBeforeTitleCase || !this.state.product || !this.state.product.id) return;

        // Clear timer if present
        if (this._nameChangeUndoTimer) {
            clearTimeout(this._nameChangeUndoTimer);
            this._nameChangeUndoTimer = null;
        }

        const original = this._lastNameBeforeTitleCase;
        this.state.loading = true;
        try {
            await this.orm.call('product.template', 'write', [[this.state.product.id], { name: original }]);
            this.state.product.name = original;
            this.state.nameChangeUndoVisible = false;
            this._lastNameBeforeTitleCase = null;
            this.notification.add(_t('Product name restored'), { type: 'success' });
        } catch (e) {
            this.notification.add(_t('Failed to restore product name: ') + (e.data?.message || e.message || String(e)), { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    focusInput() {
        if (this.barcodeInputRef.el) {
            this.barcodeInputRef.el.focus();
            this.barcodeInputRef.el.select();
        }
    }

    _playScanSound(type = "success") {
        try {
            if (!this._audioCtx) return;
            const osc = this._audioCtx.createOscillator();
            const gain = this._audioCtx.createGain();
            osc.connect(gain);
            gain.connect(this._audioCtx.destination);

            if (type === "notfound" || type === "error") {
                // A harsh, louder, lower buzzer sound for error/not found
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(250, this._audioCtx.currentTime); // 250Hz low pitch
                gain.gain.setValueAtTime(0.8, this._audioCtx.currentTime); // 80% volume (louder)

                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.35); // 350ms duration (longer)
            } else if (type === "duplicate") {
                // A distinct double-beep or slightly different tone for duplicate
                osc.type = "sine";
                osc.frequency.setValueAtTime(660, this._audioCtx.currentTime);
                gain.gain.setValueAtTime(0.6, this._audioCtx.currentTime); // 60% volume

                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.15);
            } else {
                // A pleasant, loud high-pitched beep for success
                osc.type = "sine";
                osc.frequency.setValueAtTime(880, this._audioCtx.currentTime); // 880Hz high pitch
                gain.gain.setValueAtTime(0.6, this._audioCtx.currentTime); // 60% volume (louder than before)

                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.1); // 100ms short beep
            }
        } catch (_e) {
            // Ignore errors if audio fails to play
        }
    }

    onBarcodeInput(ev) {
        this.state.barcode = ev.target.value;
        if (this._debounceTimer) {
            clearTimeout(this._debounceTimer);
        }
        this._debounceTimer = setTimeout(() => {
            if (this.state.barcode && this.state.barcode.trim().length >= 2) {
                this.searchProduct();
            }
        }, 500);
    }

    onBarcodeKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            if (this._debounceTimer) {
                clearTimeout(this._debounceTimer);
            }
            this.searchProduct();
        }
    }

    // ---- Image Update ----

    /**
     * Buka dialog pilihan: Gallery atau Camera
     */
    openImageUpdateDialog() {
        this.state.showImageUpdateModal = true;
    }

    closeImageUpdateModal() {
        this.state.showImageUpdateModal = false;
    }

    /**
     * Trigger hidden file input untuk galeri (tanpa capture)
     */
    chooseFromGallery() {
        this.state.showImageUpdateModal = false;
        if (this.galleryInputRef.el) {
            this.galleryInputRef.el.value = '';  // reset agar bisa pilih file yang sama
            this.galleryInputRef.el.click();
        }
    }

    /**
     * Trigger hidden file input untuk kamera native (dengan capture="environment")
     */
    takePhoto() {
        this.state.showImageUpdateModal = false;
        if (this.cameraInputRef.el) {
            this.cameraInputRef.el.value = '';
            this.cameraInputRef.el.click();
        }
    }

    /**
     * Handle file yang dipilih (dari galeri maupun kamera).
     * Supports iOS (HEIC, large photos) and Android.
     */
    async onImageFileSelected(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;

        // Validate image type.
        // iOS may return empty string or "image/heic" for HEIC photos.
        // We accept: any "image/*" type, empty type (iOS HEIC fallback),
        // or file extension that looks like an image.
        const validType = !file.type || file.type.startsWith('image/');
        const validExt = /\.(jpe?g|png|gif|webp|bmp|heic|heif|tiff?)$/i.test(file.name);
        if (!validType && !validExt) {
            this.notification.add(_t("Please select an image file."), { type: 'warning' });
            return;
        }

        // Max 25MB raw (iPhone 12 HEIC can be 5-8MB, but photos taken
        // in ProRAW or other formats can be larger)
        if (file.size > 25 * 1024 * 1024) {
            this.notification.add(_t("Image too large. Maximum 25MB."), { type: 'warning' });
            return;
        }

        this.state.loading = true;
        try {
            // Process: load into canvas, resize to max 1920px, convert to JPEG base64.
            // This handles HEIC conversion (browser decodes it), EXIF auto-rotation
            // (modern browsers auto-rotate on canvas draw), and reduces upload size.
            const base64 = await this._processImageFile(file);

            const result = await this.orm.call(
                'product.template',
                'update_product_image',
                [this.state.product.id, base64]
            );
            if (result.success) {
                this.state.product.image_url = result.image_url;
                this.notification.add(_t("Product image updated!"), { type: 'success' });
            } else {
                this.notification.add(
                    _t("Failed to update image: ") + (result.error || ''),
                    { type: 'danger' }
                );
            }
        } catch (e) {
            this.notification.add(
                _t("Error updating image: ") + (e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Convert current product name to Title Case and save to server.
     */
    async convertProductNameToTitleCase() {
        if (!this.state.product || !this.state.product.id) return;
        const original = (this.state.product.name || "").trim();
        if (!original) return;
        const toTitle = (s) => s.split(/\s+/).map((w) => {
            if (!w) return '';
            return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
        }).join(' ');
        const newName = toTitle(original);
        if (newName === original) {
            this.notification.add(_t("Product name already in Title Case"), { type: 'info' });
            return;
        }
        // Clear any previous undo timer
        if (this._nameChangeUndoTimer) {
            clearTimeout(this._nameChangeUndoTimer);
            this._nameChangeUndoTimer = null;
        }

        // Store original name for potential Undo
        this._lastNameBeforeTitleCase = original;

        this.state.loading = true;
        try {
            await this.orm.call('product.template', 'write', [[this.state.product.id], { name: newName }]);
            this.state.product.name = newName;

            // Show temporary Undo button for 15s
            this.state.nameChangeUndoVisible = true;
            this._nameChangeUndoTimer = setTimeout(() => {
                this.state.nameChangeUndoVisible = false;
                this._lastNameBeforeTitleCase = null;
                this._nameChangeUndoTimer = null;
            }, 15000);

            this.notification.add(_t("Product name converted to Title Case"), { type: 'success' });
        } catch (e) {
            this.notification.add(_t("Failed to update product name: ") + (e.data?.message || e.message || String(e)), { type: 'danger' });
            // clear stored original on failure
            this._lastNameBeforeTitleCase = null;
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Remove image background using Gemini AI
     */
    async autoWhiteBackground() {
        if (!this.state.product || !this.state.product.id) return;

        this.state.loading = true;
        try {
            await this.orm.call(
                'product.template',
                'action_auto_white_background',
                [[this.state.product.id]]
            );

            // Bypass browser cache to load the newly generated image
            const ts = new Date().getTime();
            if (this.state.product.image_url.includes('?')) {
                this.state.product.image_url = this.state.product.image_url.split('?')[0] + '?t=' + ts;
            } else {
                this.state.product.image_url += '?t=' + ts;
            }

            this.notification.add(_t("Background removed successfully!"), { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t("Auto White BG failed: ") + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Run professional edit (remove hands + refine) via backend
     */
    async autoProfessionalEdit() {
        if (!this.state.product || !this.state.product.id) return;

        this.state.loading = true;
        try {
            await this.orm.call(
                'product.template',
                'action_auto_professional_edit',
                [[this.state.product.id]]
            );

            // Bypass browser cache to load the newly generated image
            const ts = new Date().getTime();
            if (this.state.product.image_url.includes('?')) {
                this.state.product.image_url = this.state.product.image_url.split('?')[0] + '?t=' + ts;
            } else {
                this.state.product.image_url += '?t=' + ts;
            }

            this.notification.add(_t("Professional edit completed!"), { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t("Auto Pro Edit failed: ") + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Load image file into canvas, resize to max 1920px, output as JPEG base64.
     * Works on iOS (HEIC decoded by browser), Android, and desktop.
     * Returns base64 string WITHOUT "data:...;base64," prefix.
     */
    _processImageFile(file) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const objectUrl = URL.createObjectURL(file);

            img.onload = () => {
                URL.revokeObjectURL(objectUrl);
                const maxDim = 1920;
                let w = img.naturalWidth;
                let h = img.naturalHeight;

                // Scale down if larger than maxDim
                if (w > maxDim || h > maxDim) {
                    if (w >= h) {
                        h = Math.round(h * (maxDim / w));
                        w = maxDim;
                    } else {
                        w = Math.round(w * (maxDim / h));
                        h = maxDim;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);

                // Convert to JPEG at 85% quality — good balance of size and quality
                const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
                const base64 = dataUrl.split(',')[1];
                resolve(base64);
            };

            img.onerror = () => {
                URL.revokeObjectURL(objectUrl);
                reject(new Error(_t("Failed to load image. The format may not be supported by your browser.")));
            };

            img.src = objectUrl;
        });
    }

    onPricelistChange(ev) {
        this.state.selectedPricelistId = ev.target.value ? parseInt(ev.target.value) : null;
        if (this.state.product) {
            this.searchProduct(this.state.product.barcode || this.state.product.default_code || this.state.product.name);
        }
        // Refresh the Product List drawer with new pricelist prices
        // (only if it has been initialized, to avoid a wasted first load).
        if (this.state.productListInitialized) {
            this.loadProductList(true);
        }
    }


    async searchProduct(overrideBarcode = null) {
        const barcode = overrideBarcode || this.state.barcode;
        if (!barcode || !barcode.trim()) {
            return;
        }

        this.state.loading = true;
        this.state.notFound = false;

        try {
            const result = await this.orm.call(
                "product.template",
                "search_product_by_barcode",
                [barcode.trim(), this.state.selectedPricelistId]
            );

            if (result.found) {
                this.state.product = result.data;
                // Initialize meta category autocomplete query for the current product
                this.state.metaCategQuery = result.data.categ_name || "";
                this.state.metaCategSuggestions = [];
                this.state.metaCategActiveSuggestion = -1;
                this.state.showMetaCategDropdown = false;
                this.state.notFound = false;
                this.state.showCreateForm = false;
                this.addToHistory(result.data);
                this.state.barcode = "";
                this.focusInput();
                if (this.state.autoAddToPrintList) {
                    await this.addToPrintList(true);
                }
            } else {
                this.state.product = null;
                this.state.metaCategQuery = "";
                this.state.metaCategSuggestions = [];
                this.state.metaCategActiveSuggestion = -1;
                this.state.showMetaCategDropdown = false;
                this.state.notFound = true;
                this.state.searchedCode = barcode.trim();
            }
        } catch (error) {
            this.notification.add(_t("Search failed: ") + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    addToHistory(productData) {
        this.state.history = this.state.history.filter(
            (h) => h.id !== productData.id
        );
        this.state.history.unshift({
            id: productData.id,
            name: productData.name,
            barcode: productData.barcode,
            default_code: productData.default_code,
            image_url: productData.image_url,
            price: productData.price,
            qty_on_hand: productData.qty_on_hand,
            currency_symbol: productData.currency_symbol,
            currency_position: productData.currency_position,
            timestamp: new Date().toLocaleTimeString(),
        });
        if (this.state.history.length > 20) {
            this.state.history = this.state.history.slice(0, 20);
        }
        try {
            window.localStorage.setItem("andykanoz_pc_history", JSON.stringify(this.state.history));
        } catch (e) {
            console.warn("Could not save history to localStorage", e);
        }
    }


    onHistoryClick(historyItem) {
        const searchTerm = historyItem.barcode || historyItem.default_code || historyItem.name;
        this.state.barcode = searchTerm;
        this.searchProduct(searchTerm);
        if (window.innerWidth <= 768) {
            this.state.sidebarOpen = false;
        }
    }

    clearHistory() {
        this.state.history = [];
        try {
            window.localStorage.removeItem("andykanoz_pc_history");
        } catch (e) { }
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    closeSidebar() {
        this.state.sidebarOpen = false;
    }

    // ============ PRINT LIST ============
    onAutoAddToggle(ev) {
        this.state.autoAddToPrintList = ev.target.checked;
    }

    async addToPrintList(silent = false) {
        if (!this.state.product) {
            return;
        }
        try {
            const result = await this.orm.call(
                "product.template",
                "add_to_print_list",
                [this.state.product.id]
            );
            if (result.success) {
                if (!result.already_exists && result.item) {
                    this.state.printList.push(result.item);
                }
                if (!silent) {
                    if (result.already_exists) {
                        this.notification.add(
                            _t("Product already in print list"),
                            { type: "info" }
                        );
                    } else {
                        this.notification.add(
                            _t("Added to print list"),
                            { type: "success" }
                        );
                    }
                }
                return result;
            } else {
                this.notification.add(
                    result.error || _t("Failed to add to print list"),
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(_t("Error: ") + error.message, {
                type: "danger",
            });
        }
        return null;
    }


    async removeFromPrintList(productId) {
        try {
            const result = await this.orm.call(
                "product.template",
                "remove_from_print_list",
                [productId]
            );
            if (result.success) {
                this.state.printList = this.state.printList.filter(
                    (p) => p.id !== productId
                );
            }
        } catch (error) {
            this.notification.add(_t("Error: ") + error.message, {
                type: "danger",
            });
        }
    }

    async clearPrintList() {
        if (!this.state.printList.length) return;
        try {
            const result = await this.orm.call(
                "product.template",
                "clear_print_list",
                []
            );
            if (result.success) {
                this.state.printList = [];
                this.notification.add(_t("Print list cleared"), {
                    type: "success",
                });
            }
        } catch (error) {
            this.notification.add(_t("Error: ") + error.message, {
                type: "danger",
            });
        }
    }

    async printLabels() {
        if (!this.state.printList.length) {
            this.notification.add(_t("Print list is empty"), { type: "warning" });
            return;
        }
        try {
            const result = await this.orm.call(
                "product.template",
                "get_print_list_action",
                []
            );
            if (result.success && result.action) {
                this.state.printListPanelOpen = false;
                this.action.doAction(result.action);
            } else {
                this.notification.add(
                    result.error || _t("Cannot open print dialog"),
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(_t("Error: ") + error.message, {
                type: "danger",
            });
        }
    }

    togglePrintListPanel() {
        this.state.printListPanelOpen = !this.state.printListPanelOpen;
    }

    closePrintListPanel() {
        this.state.printListPanelOpen = false;
    }

    isInPrintList(productId) {
        return this.state.printList.some((p) => p.id === productId);
    }


    // ============ CREATE FORM ============
    openCreateForm() {
        this.state.showCreateForm = true;
        this.state.createForm = {
            name: "",
            barcode: this.state.searchedCode,
            default_code: "",
            standard_price: 0,
            list_price: 0,
            categ_id: this.state.categories.length > 0 ? this.state.categories[0].id : null,
            is_published: true,
            sale_ok: true,
            purchase_ok: true,
            available_in_pos: true,
            is_storable: true,
            public_categ_ids: [],
            product_tag_ids: [],
            pricelist_id: this.state.selectedPricelistId,
            pricelist_price: 0,
        };
    }

    cancelCreateForm() {
        this.state.showCreateForm = false;
    }

    onNameInput(ev) {
        this.state.createForm.name = ev.target.value;
    }

    /**
     * Title-case the current Name input value. Each whitespace-separated
     * word gets its first character uppercased; the rest stays as typed.
     * Trailing/leading whitespace is preserved so the caret feels natural
     * if the user clicks the button mid-typing.
     *
     * Examples:
     *   "andyka noz"         -> "Andyka Noz"
     *   "BAKSO sapi aci"     -> "BAKSO Sapi Aci"   (already-upper words untouched)
     *   "mie goreng  spesial" -> "Mie Goreng  Spesial" (double-space preserved)
     */
    applyTitleCaseToName() {
        const raw = this.state.createForm.name || "";
        if (!raw.trim()) return;
        // Split on whitespace but KEEP separators via capturing group so
        // runs of spaces are preserved when we join back.
        const parts = raw.split(/(\s+)/);
        const titled = parts.map((part) => {
            if (!part || /^\s+$/.test(part)) return part;
            return part.charAt(0).toUpperCase() + part.slice(1);
        }).join("");
        this.state.createForm.name = titled;
    }
    onBarcodeFormInput(ev) {
        this.state.createForm.barcode = ev.target.value;
    }
    onDefaultCodeInput(ev) {
        this.state.createForm.default_code = ev.target.value;
    }
    onStandardPriceInput(ev) {
        this.state.createForm.standard_price = ev.target.value;
    }
    onListPriceInput(ev) {
        this.state.createForm.list_price = ev.target.value;
    }
    onPricelistPriceInput(ev) {
        this.state.createForm.pricelist_price = ev.target.value;
    }
    onIsPublishedToggle(ev) {
        this.state.createForm.is_published = ev.target.checked;
    }

    onCategorySelect(value) {
        this.state.createForm.categ_id = value;
    }
    onMetaCategoryInput(ev) {
        const q = ev.target.value;
        this.state.metaCategQuery = q;
        if (this._metaCategDebounce) clearTimeout(this._metaCategDebounce);
        this._metaCategDebounce = setTimeout(() => this._filterMetaCategSuggestions(q), 200);
    }

    onMetaCategoryFocus() {
        this._filterMetaCategSuggestions(this.state.metaCategQuery || "");
        this.state.showMetaCategDropdown = true;
    }

    onMetaCategoryBlur() {
        setTimeout(() => { this.state.showMetaCategDropdown = false; }, 150);
    }

    onMetaCategoryKeydown(ev) {
        const list = this.state.metaCategSuggestions || [];
        const len = list.length;

        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            if (!this.state.showMetaCategDropdown) {
                this._filterMetaCategSuggestions(this.state.metaCategQuery || "");
                return;
            }
            if (len > 0) {
                this.state.metaCategActiveSuggestion = (this.state.metaCategActiveSuggestion + 1) % len;
                this._scrollToActiveSuggestion();
            }
            return;
        }
        if (ev.key === "ArrowUp") {
            ev.preventDefault();
            if (len > 0) {
                this.state.metaCategActiveSuggestion = (this.state.metaCategActiveSuggestion - 1 + len) % len;
                this._scrollToActiveSuggestion();
            }
            return;
        }
        if (ev.key === "Home" && this.state.showMetaCategDropdown && len > 0) {
            ev.preventDefault();
            this.state.metaCategActiveSuggestion = 0;
            this._scrollToActiveSuggestion();
            return;
        }
        if (ev.key === "End" && this.state.showMetaCategDropdown && len > 0) {
            ev.preventDefault();
            this.state.metaCategActiveSuggestion = len - 1;
            this._scrollToActiveSuggestion();
            return;
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            const idx = this.state.metaCategActiveSuggestion >= 0 ? this.state.metaCategActiveSuggestion : 0;
            if (list[idx]) {
                this.selectMetaCateg(list[idx]);
            } else if (this.state.metaCategShowQuickCreate && this.state.metaCategQuery.trim()) {
                this.quickCreateCategory();
            }
            return;
        }
        if (ev.key === "Tab") {
            // Select active suggestion on Tab, then let focus move naturally
            if (this.state.showMetaCategDropdown && len > 0) {
                const idx = this.state.metaCategActiveSuggestion >= 0 ? this.state.metaCategActiveSuggestion : 0;
                if (list[idx] && !list[idx].isCreate) {
                    this.selectMetaCateg(list[idx]);
                }
            }
            this.state.showMetaCategDropdown = false;
            this.state.metaCategActiveSuggestion = -1;
            return;
        }
        if (ev.key === "Escape") {
            ev.preventDefault();
            this.state.showMetaCategDropdown = false;
            this.state.metaCategActiveSuggestion = -1;
            ev.target.blur();
        }
    }

    _filterMetaCategSuggestions(query) {
        const all = this.state.categories || [];
        const q = (query || "").trim().toLowerCase();

        let matched = [];
        if (!q) {
            matched = all.slice(0, 50).map(c => this._formatCategoryItem(c, ""));
        } else {
            matched = all.filter(c => (c.complete_name || c.name || '').toLowerCase().includes(q))
                .slice(0, 50)
                .map(c => this._formatCategoryItem(c, q));
        }

        // Add create suggestion
        const exactExists = all.some(c => ((c.complete_name || c.name || '').toLowerCase() === q));
        if (!exactExists && q) {
            const createItem = {
                id: `__create__${String(query)}_${Date.now()}`,
                name: query,
                isCreate: true,
                _create_name: query,
            };
            matched.unshift(createItem);
        }

        this.state.metaCategSuggestions = matched;
        this.state.metaCategActiveSuggestion = matched.length > 0 ? 0 : -1;
        this.state.showMetaCategDropdown = true;
    }

    _formatCategoryItem(category, query) {
        const fullName = category.complete_name || category.name || '';
        if (!query) return { ...category, parts: [{ text: fullName, match: false }] };

        const lowerName = fullName.toLowerCase();
        const idx = lowerName.indexOf(query);
        if (idx === -1) return { ...category, parts: [{ text: fullName, match: false }] };

        return {
            ...category,
            parts: [
                { text: fullName.substring(0, idx), match: false },
                { text: fullName.substring(idx, idx + query.length), match: true },
                { text: fullName.substring(idx + query.length), match: false }
            ]
        };
    }

    toggleMetaCategoryDropdown(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.showMetaCategDropdown) {
            this.state.showMetaCategDropdown = false;
        } else {
            this._filterMetaCategSuggestions("");
            const input = document.querySelector('.o_pc_meta_ac_input');
            if (input) input.focus();
        }
    }

    _scrollToActiveSuggestion() {
        setTimeout(() => {
            const dropdown = document.querySelector('.o_pc_meta_ac_dropdown');
            const activeItem = document.querySelector('.o_pc_meta_ac_item.o_pc_active');
            if (dropdown && activeItem) {
                const offsetBottom = activeItem.offsetTop + activeItem.offsetHeight;
                const scrollBottom = dropdown.scrollTop + dropdown.offsetHeight;
                if (offsetBottom > scrollBottom) {
                    dropdown.scrollTop = offsetBottom - dropdown.offsetHeight;
                } else if (activeItem.offsetTop < dropdown.scrollTop) {
                    dropdown.scrollTop = activeItem.offsetTop;
                }
            }
        }, 0);
    }

    // ── Ecommerce Category (public_categ_ids) multi-select autocomplete ──

    onPubCategContainerClick(ev) {
        // Click anywhere in the container focuses the input
        const input = ev.currentTarget.querySelector('.o_pc_m2m_input');
        if (input && ev.target !== input) {
            input.focus();
        }
    }

    onPubCategInput(ev) {
        const q = ev.target.value;
        this.state.pubCategQuery = q;
        if (this._pubCategDebounce) clearTimeout(this._pubCategDebounce);
        this._pubCategDebounce = setTimeout(() => this._filterPubCategSuggestions(q), 200);
    }

    onPubCategFocus() {
        this._filterPubCategSuggestions(this.state.pubCategQuery || "");
        this.state.showPubCategDropdown = true;
    }

    onPubCategBlur() {
        setTimeout(() => {
            this.state.showPubCategDropdown = false;
            this.state.pubCategActiveSuggestion = -1;
        }, 200);
    }

    onPubCategKeydown(ev) {
        const list = this.state.pubCategSuggestions || [];
        const len = list.length;

        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            if (!this.state.showPubCategDropdown) {
                this._filterPubCategSuggestions(this.state.pubCategQuery || "");
                return;
            }
            if (len > 0) {
                this.state.pubCategActiveSuggestion = (this.state.pubCategActiveSuggestion + 1) % len;
                this._scrollPubCategToActive();
            }
            return;
        }
        if (ev.key === "ArrowUp") {
            ev.preventDefault();
            if (len > 0) {
                this.state.pubCategActiveSuggestion = (this.state.pubCategActiveSuggestion - 1 + len) % len;
                this._scrollPubCategToActive();
            }
            return;
        }
        if (ev.key === "Home" && this.state.showPubCategDropdown && len > 0) {
            ev.preventDefault();
            this.state.pubCategActiveSuggestion = 0;
            this._scrollPubCategToActive();
            return;
        }
        if (ev.key === "End" && this.state.showPubCategDropdown && len > 0) {
            ev.preventDefault();
            this.state.pubCategActiveSuggestion = len - 1;
            this._scrollPubCategToActive();
            return;
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            const idx = this.state.pubCategActiveSuggestion >= 0 ? this.state.pubCategActiveSuggestion : 0;
            if (list[idx]) {
                this.selectPubCateg(list[idx]);
            }
            return;
        }
        if (ev.key === "Tab") {
            // Select active suggestion on Tab, then let focus move naturally
            if (this.state.showPubCategDropdown && len > 0) {
                const idx = this.state.pubCategActiveSuggestion >= 0 ? this.state.pubCategActiveSuggestion : 0;
                if (list[idx] && !list[idx].isCreate) {
                    this.selectPubCateg(list[idx]);
                }
            }
            this.state.showPubCategDropdown = false;
            this.state.pubCategActiveSuggestion = -1;
            return;
        }
        if (ev.key === "Backspace" && !this.state.pubCategQuery) {
            // Remove last tag when Backspace on empty input
            const tags = this.state.product && this.state.product.public_categ_ids;
            if (tags && tags.length > 0) {
                this.removePubCateg(tags[tags.length - 1].id);
            }
            return;
        }
        if (ev.key === "Escape") {
            ev.preventDefault();
            this.state.showPubCategDropdown = false;
            this.state.pubCategActiveSuggestion = -1;
            ev.target.blur();
        }
    }

    _filterPubCategSuggestions(query) {
        const all = this.state.publicCategories || [];
        const selected = (this.state.product && this.state.product.public_categ_ids) || [];
        const selectedIds = new Set(selected.map(c => c.id));
        const q = (query || "").trim().toLowerCase();

        // Show all categories with _selected flag (checkbox style)
        let matched = [];
        if (!q) {
            matched = all.slice(0, 80).map(c => ({
                ...this._formatPubCategItem(c, ""),
                _selected: selectedIds.has(c.id),
            }));
        } else {
            const displayField = (c) => (c.display_name || c.name || '').toLowerCase();
            matched = all.filter(c => displayField(c).includes(q))
                .slice(0, 80)
                .map(c => ({
                    ...this._formatPubCategItem(c, q),
                    _selected: selectedIds.has(c.id),
                }));
        }

        // Add create option if no exact match exists
        const exactExists = all.some(c => (c.display_name || c.name || '').toLowerCase() === q);
        if (!exactExists && q) {
            matched.push({
                id: `__create__pub_${query}_${Date.now()}`,
                name: query,
                isCreate: true,
                _create_name: query,
            });
        }

        this.state.pubCategSuggestions = matched;
        this.state.pubCategActiveSuggestion = matched.length > 0 ? 0 : -1;
        this.state.showPubCategDropdown = true;
    }

    _formatPubCategItem(category, query) {
        const name = category.display_name || category.name || '';
        if (!query) return { ...category, parts: [{ text: name, match: false }] };
        const idx = name.toLowerCase().indexOf(query);
        if (idx === -1) return { ...category, parts: [{ text: name, match: false }] };
        return {
            ...category,
            parts: [
                { text: name.substring(0, idx), match: false },
                { text: name.substring(idx, idx + query.length), match: true },
                { text: name.substring(idx + query.length), match: false },
            ],
        };
    }

    togglePubCategDropdown(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.showPubCategDropdown) {
            this.state.showPubCategDropdown = false;
        } else {
            this._filterPubCategSuggestions("");
            const input = document.querySelector('.o_pc_m2m_input');
            if (input) input.focus();
        }
    }

    _scrollPubCategToActive() {
        setTimeout(() => {
            const dropdown = document.querySelector('.o_pc_m2m_dropdown');
            const activeItem = dropdown && dropdown.querySelector('.o_pc_m2m_dropdown_item.o_pc_active');
            if (dropdown && activeItem) {
                const offsetBottom = activeItem.offsetTop + activeItem.offsetHeight;
                const scrollBottom = dropdown.scrollTop + dropdown.offsetHeight;
                if (offsetBottom > scrollBottom) {
                    dropdown.scrollTop = offsetBottom - dropdown.offsetHeight;
                } else if (activeItem.offsetTop < dropdown.scrollTop) {
                    dropdown.scrollTop = activeItem.offsetTop;
                }
            }
        }, 0);
    }

    async selectPubCateg(categ) {
        if (!categ || !this.state.product) return;

        if (categ.isCreate) {
            await this.quickCreatePubCateg(categ._create_name || categ.name);
            return;
        }

        // Toggle: if already selected, remove; otherwise add
        const current = [...(this.state.product.public_categ_ids || [])];
        const existingIdx = current.findIndex(c => c.id === categ.id);
        if (existingIdx >= 0) {
            current.splice(existingIdx, 1);
        } else {
            current.push({ id: categ.id, name: categ.display_name || categ.name });
        }

        await this._savePubCategIds(current);
        // Keep dropdown open for multi-select and refresh suggestions
        this._filterPubCategSuggestions(this.state.pubCategQuery || "");
    }

    async removePubCateg(categId) {
        if (!this.state.product) return;
        const current = (this.state.product.public_categ_ids || []).filter(c => c.id !== categId);
        await this._savePubCategIds(current);
    }

    async _savePubCategIds(list) {
        const ids = list.map(c => c.id);
        this.state.loading = true;
        try {
            await this.orm.call('product.template', 'write', [
                [this.state.product.id],
                { public_categ_ids: [[6, 0, ids]] },
            ]);
            this.state.product.public_categ_ids = list;
            this.notification.add(_t('Ecommerce categories updated'), { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t('Failed to update ecommerce categories: ') + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async quickCreatePubCateg(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        this.state.loading = true;
        try {
            const newId = await this.orm.call('product.public.category', 'create', [{ name }]);
            await this.loadConfig();
            // Add to current product's selected list
            const current = [...(this.state.product.public_categ_ids || [])];
            current.push({ id: newId, name });
            await this._savePubCategIds(current);
            this.state.pubCategQuery = "";
            this.state.pubCategSuggestions = [];
            this.state.pubCategActiveSuggestion = -1;
            this.state.showPubCategDropdown = false;
            this.notification.add(_t('Ecommerce category created: ') + name, { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t('Failed to create ecommerce category: ') + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    // ── Product Tags (product_tag_ids) multi-select autocomplete ──

    onTagContainerClick(ev) {
        const input = ev.currentTarget.querySelector('.o_pc_m2m_input');
        if (input && ev.target !== input) input.focus();
    }

    onTagInput(ev) {
        const q = ev.target.value;
        this.state.tagQuery = q;
        if (this._tagDebounce) clearTimeout(this._tagDebounce);
        this._tagDebounce = setTimeout(() => this._filterTagSuggestions(q), 200);
    }

    onTagFocus() {
        this._filterTagSuggestions(this.state.tagQuery || "");
        this.state.showTagDropdown = true;
    }

    onTagBlur() {
        setTimeout(() => {
            this.state.showTagDropdown = false;
            this.state.tagActiveSuggestion = -1;
        }, 200);
    }

    onTagKeydown(ev) {
        const list = this.state.tagSuggestions || [];
        const len = list.length;

        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            if (!this.state.showTagDropdown) {
                this._filterTagSuggestions(this.state.tagQuery || "");
                return;
            }
            if (len > 0) {
                this.state.tagActiveSuggestion = (this.state.tagActiveSuggestion + 1) % len;
                this._scrollTagToActive();
            }
            return;
        }
        if (ev.key === "ArrowUp") {
            ev.preventDefault();
            if (len > 0) {
                this.state.tagActiveSuggestion = (this.state.tagActiveSuggestion - 1 + len) % len;
                this._scrollTagToActive();
            }
            return;
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            const idx = this.state.tagActiveSuggestion >= 0 ? this.state.tagActiveSuggestion : 0;
            if (list[idx]) this.selectTag(list[idx]);
            return;
        }
        if (ev.key === "Backspace" && !this.state.tagQuery) {
            const tags = this.state.product && this.state.product.product_tag_ids;
            if (tags && tags.length > 0) {
                this.removeTag(tags[tags.length - 1].id);
            }
            return;
        }
        if (ev.key === "Escape") {
            ev.preventDefault();
            this.state.showTagDropdown = false;
            this.state.tagActiveSuggestion = -1;
            ev.target.blur();
        }
    }

    _filterTagSuggestions(query) {
        const all = this.state.productTags || [];
        const selected = (this.state.product && this.state.product.product_tag_ids) || [];
        const selectedIds = new Set(selected.map(c => c.id));
        const q = (query || "").trim().toLowerCase();

        let matched = [];
        if (!q) {
            matched = all.slice(0, 80).map(c => ({
                ...this._formatTagItem(c, ""),
                _selected: selectedIds.has(c.id),
            }));
        } else {
            matched = all.filter(c => (c.name || '').toLowerCase().includes(q))
                .slice(0, 80)
                .map(c => ({
                    ...this._formatTagItem(c, q),
                    _selected: selectedIds.has(c.id),
                }));
        }

        const exactExists = all.some(c => (c.name || '').toLowerCase() === q);
        if (!exactExists && q) {
            matched.push({
                id: `__create__tag_${query}_${Date.now()}`,
                name: query,
                isCreate: true,
                _create_name: query,
            });
        }

        this.state.tagSuggestions = matched;
        this.state.tagActiveSuggestion = matched.length > 0 ? 0 : -1;
        this.state.showTagDropdown = true;
    }

    _formatTagItem(tag, query) {
        const name = tag.name || '';
        if (!query) return { ...tag, parts: [{ text: name, match: false }] };
        const idx = name.toLowerCase().indexOf(query);
        if (idx === -1) return { ...tag, parts: [{ text: name, match: false }] };
        return {
            ...tag,
            parts: [
                { text: name.substring(0, idx), match: false },
                { text: name.substring(idx, idx + query.length), match: true },
                { text: name.substring(idx + query.length), match: false },
            ],
        };
    }

    toggleTagDropdown(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.showTagDropdown) {
            this.state.showTagDropdown = false;
        } else {
            this._filterTagSuggestions("");
            const input = ev.currentTarget.closest('.o_pc_meta_item').querySelector('.o_pc_m2m_input');
            if (input) input.focus();
        }
    }

    _scrollTagToActive() {
        setTimeout(() => {
            const dropdowns = document.querySelectorAll('.o_pc_m2m_dropdown');
            dropdowns.forEach(dropdown => {
                const activeItem = dropdown.querySelector('.o_pc_m2m_dropdown_item.o_pc_active');
                if (activeItem) {
                    const offsetBottom = activeItem.offsetTop + activeItem.offsetHeight;
                    const scrollBottom = dropdown.scrollTop + dropdown.offsetHeight;
                    if (offsetBottom > scrollBottom) {
                        dropdown.scrollTop = offsetBottom - dropdown.offsetHeight;
                    } else if (activeItem.offsetTop < dropdown.scrollTop) {
                        dropdown.scrollTop = activeItem.offsetTop;
                    }
                }
            });
        }, 0);
    }

    async selectTag(tag) {
        if (!tag || !this.state.product) return;
        if (tag.isCreate) {
            await this.quickCreateTag(tag._create_name || tag.name);
            return;
        }

        const current = [...(this.state.product.product_tag_ids || [])];
        const existingIdx = current.findIndex(c => c.id === tag.id);
        if (existingIdx >= 0) {
            current.splice(existingIdx, 1);
        } else {
            current.push({ id: tag.id, name: tag.name });
        }

        await this._saveTagIds(current);
        this._filterTagSuggestions(this.state.tagQuery || "");
    }

    async removeTag(tagId) {
        if (!this.state.product) return;
        const current = (this.state.product.product_tag_ids || []).filter(c => c.id !== tagId);
        await this._saveTagIds(current);
    }

    async _saveTagIds(list) {
        const ids = list.map(c => c.id);
        this.state.loading = true;
        try {
            await this.orm.call('product.template', 'write', [
                [this.state.product.id],
                { product_tag_ids: [[6, 0, ids]] },
            ]);
            this.state.product.product_tag_ids = list;
            this.notification.add(_t('Product tags updated'), { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t('Failed to update product tags: ') + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async quickCreateTag(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        this.state.loading = true;
        try {
            const newId = await this.orm.call('product.tag', 'create', [{ name }]);
            await this.loadConfig(); // Refresh tags
            const current = [...(this.state.product.product_tag_ids || [])];
            current.push({ id: newId, name });
            await this._saveTagIds(current);
            this.state.tagQuery = "";
            this.state.tagSuggestions = [];
            this.state.tagActiveSuggestion = -1;
            this.state.showTagDropdown = false;
            this.notification.add(_t('Product tag created: ') + name, { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t('Failed to create product tag: ') + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    selectMetaCateg(categ) {
        if (!categ) return;

        // If this is a "create new" suggestion, instantly create the category
        if (categ.isCreate) {
            this.state.metaCategQuery = categ._create_name || categ.name || "";
            this.state.metaCategSuggestions = [];
            this.state.metaCategActiveSuggestion = -1;
            this.state.showMetaCategDropdown = false;
            this.quickCreateCategory();
            return;
        }

        this.state.metaCategQuery = categ.complete_name || categ.name || "";
        this.state.metaCategSuggestions = [];
        this.state.metaCategActiveSuggestion = -1;
        this.state.showMetaCategDropdown = false;
        // persist to server
        this.onMetaCategorySelect(categ.id);
    }
    async onMetaCategorySelect(valueOrEvent) {
        if (!this.state.product) return;
        let value = valueOrEvent;
        // Support both SelectMenu (value) and native <select> (event)
        if (value && value.target && typeof value.target.value !== 'undefined') {
            value = value.target.value;
        }
        const newCatId = value ? parseInt(value, 10) : false;
        const oldCatId = this.state.product.categ_id;
        if (newCatId === oldCatId) return;
        this.state.loading = true;
        try {
            await this.orm.call('product.template', 'write', [[this.state.product.id], { categ_id: newCatId }]);
            // Refresh product so any pricelist changes linked to category take effect immediately
            const lookupTerm = this.state.product.barcode || this.state.product.default_code || this.state.product.name;
            if (lookupTerm) {
                await this.searchProduct(lookupTerm);
            }
            this.notification.add(_t('Category updated'), { type: 'success' });
        } catch (e) {
            this.notification.add(_t('Failed to update category: ') + (e.data?.message || e.message || String(e)), { type: 'danger' });
        } finally {
            this.state.loading = false;
        }
    }

    async quickCreateCategory() {
        const name = (this.state.metaCategQuery || "").trim();
        if (!name) return;
        this.state.loading = true;
        try {
            const newId = await this.orm.call('product.category', 'create', [{ name }]);
            // Reload categories to get the full record with complete_name
            await this.loadConfig();
            const cat = (this.state.categories || []).find((c) => c.id === newId);
            if (cat) {
                this.state.metaCategQuery = cat.complete_name || cat.name || "";
            } else {
                this.state.metaCategQuery = name;
            }
            this.state.metaCategSuggestions = [];
            this.state.metaCategActiveSuggestion = -1;
            this.state.showMetaCategDropdown = false;
            this.state.metaCategShowQuickCreate = false;
            // Persist selection to the current product
            if (this.state.product) {
                await this.onMetaCategorySelect(newId);
            }
            this.notification.add(_t('Category created and applied: ') + name, { type: 'success' });
        } catch (e) {
            this.notification.add(
                _t('Failed to create category: ') + (e.data?.message || e.message || String(e)),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async openCreateCategory(nameOrEvent) {
        // Handle case where openCreateCategory is called from XML click event without arguments
        let defaultName = null;
        if (nameOrEvent && typeof nameOrEvent === 'string') {
            defaultName = nameOrEvent;
        }

        // Open a modal form to create a new product category.
        // After the modal closes, refresh categories and auto-select the new one.
        const existingIds = new Set((this.state.categories || []).map((c) => c.id));
        let actionResult = null;

        const actionContext = defaultName ? { default_name: defaultName } : {};

        try {
            actionResult = await new Promise((resolve) => {
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: _t('Create Product Category'),
                    res_model: 'product.category',
                    views: [[false, 'form']],
                    target: 'new',
                    context: actionContext,
                }, {
                    onClose: () => {
                        resolve(true); // Resolve when modal is closed
                    }
                });
            });
        } catch (e) {
            // If the modal was dismissed or action failed, still try to refresh
            console.warn("[ProductChecker] Create Category dialog closed with error:", e);
        }
        await this.loadConfig();
        const newCat = (this.state.categories || []).find((c) => !existingIds.has(c.id));
        const newId = newCat ? newCat.id : (actionResult && actionResult.res_id ? actionResult.res_id : null);
        if (newId) {
            const cat = (this.state.categories || []).find((c) => c.id === newId);
            if (cat) {
                this.state.metaCategQuery = cat.complete_name || cat.name || "";
                try {
                    await this.onMetaCategorySelect(newId);
                } catch (_e) { }
            }
        }
    }
    onCreateFormPricelistSelect(value) {
        this.state.createForm.pricelist_id = value;
    }
    onPublicCategoriesSelect(values) {
        this.state.createForm.public_categ_ids = Array.isArray(values) ? values : [];
    }

    onProductTagsSelect(values) {
        this.state.createForm.product_tag_ids = Array.isArray(values) ? values : [];
    }

    async submitCreateForm() {
        const form = this.state.createForm;
        if (!form.name || !form.name.trim()) {
            this.notification.add(_t("Product Name is required"), { type: "warning" });
            return;
        }

        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "product.template",
                "quick_create_from_checker",
                [{
                    name: form.name.trim(),
                    barcode: form.barcode || "",
                    default_code: form.default_code || "",
                    standard_price: parseFloat(form.standard_price) || 0,
                    list_price: parseFloat(form.list_price) || 0,
                    categ_id: form.categ_id,
                    is_published: form.is_published,
                    sale_ok: form.sale_ok,
                    purchase_ok: form.purchase_ok,
                    available_in_pos: form.available_in_pos,
                    is_storable: form.is_storable,
                    public_categ_ids: form.public_categ_ids,
                    product_tag_ids: form.product_tag_ids,
                    pricelist_id: form.pricelist_id,
                    pricelist_price: parseFloat(form.pricelist_price) || 0,
                }]
            );

            if (result.success) {
                this.notification.add(_t("Product created successfully"), {
                    type: "success",
                });
                this.state.product = result.data;
                this.state.metaCategQuery = result.data.categ_name || "";
                this.state.metaCategSuggestions = [];
                this.state.metaCategActiveSuggestion = -1;
                this.state.showMetaCategDropdown = false;
                this.state.notFound = false;
                this.state.showCreateForm = false;
                this.addToHistory(result.data);
                this.state.barcode = result.data.barcode || result.data.default_code || "";
            } else {
                this.notification.add(result.error || _t("Failed to create product"), {
                    type: "danger",
                });
            }
        } catch (error) {
            this.notification.add(_t("Create failed: ") + error.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    openProductForm() {
        if (!this.state.product) return;

        // Save current code to sessionStorage so it restores when clicking breadcrumbs back
        const currentCode = this.state.searchedCode || this.state.barcode || this.state.product.barcode || this.state.product.default_code || this.state.product.name;
        if (currentCode) {
            window.sessionStorage.setItem("pc_return_restore", currentCode);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.template",
            res_id: this.state.product.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openCategoryForm() {
        // Open the selected category in a popup form view
        const catId = this.state.product && this.state.product.categ_id ? this.state.product.categ_id : null;
        if (!catId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'product.category',
            res_id: catId,
            views: [[false, 'form']],
            target: 'new',
        }, {
            onClose: async () => {
                // Refresh configuration to catch any category renames
                await this.loadConfig();
                const cat = (this.state.categories || []).find((c) => c.id === catId);
                if (cat) {
                    this.state.product.categ_name = cat.complete_name || cat.name;
                    this.state.metaCategQuery = this.state.product.categ_name;
                }
            }
        });
    }

    async onKpiAction(actionType) {
        if (!this.state.product) return;

        if (actionType === 'price') {
            const catId = this.state.product.categ_id || null;
            const pricelistId = this.state.selectedPricelistId || null;

            let existingItemId = null;
            if (catId && pricelistId) {
                try {
                    // Search for an existing rule applied to this category in the active pricelist
                    const result = await this.orm.call(
                        'product.pricelist.item',
                        'search',
                        [[
                            ['pricelist_id', '=', pricelistId],
                            ['applied_on', '=', '2_product_category'],
                            ['categ_id', '=', catId]
                        ]],
                        { limit: 1 }
                    );
                    if (result && result.length > 0) {
                        existingItemId = result[0];
                    }
                } catch (e) {
                    console.warn("[ProductChecker] Failed to search existing pricelist item", e);
                }
            }

            const context = {
                default_applied_on: catId ? '2_product_category' : '1_product',
                default_product_tmpl_id: this.state.product.id,
                default_categ_id: catId,
                default_pricelist_id: pricelistId,
            };

            const actionOpts = {
                type: 'ir.actions.act_window',
                name: _t('Open: Pricelist Rules'),
                res_model: 'product.pricelist.item',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            };

            // If an existing rule is found, open it in edit mode
            if (existingItemId) {
                actionOpts.res_id = existingItemId;
            }

            this.action.doAction(actionOpts, {
                onClose: () => {
                    // Refresh product data so the new price is reflected immediately
                    const lookupTerm = this.state.product.barcode || this.state.product.default_code || this.state.product.name;
                    if (lookupTerm) {
                        this.searchProduct(lookupTerm);
                    }
                }
            });
            return;
        }

        if (actionType === 'cost') {
            this.state.editCostValue = this.state.product.standard_price || 0;
            this.state.showCostUpdateModal = true;
            setTimeout(() => {
                if (this.costInputRef.el) {
                    this.costInputRef.el.focus();
                    this.costInputRef.el.select();
                }
            }, 50);
            return;
        }

        if (actionType === 'stock') {
            this.state.editStockValue = this.state.product.qty_on_hand || 0;
            this.state.showStockUpdateModal = true;
            setTimeout(() => {
                if (this.stockInputRef.el) {
                    this.stockInputRef.el.focus();
                    this.stockInputRef.el.select();
                }
            }, 50);
            return;
        }

        // Placeholder handler for other KPI action buttons
        console.debug("[ProductChecker] KPI action:", actionType, "product:", this.state.product && this.state.product.id);
        this.notification.add(_t("Action '" + actionType + "' is not implemented yet."), { type: "info" });
    }

    /**
     * Create a dedicated pricelist for the current product and open the
     * pricelist item create form with the product pre-filled so the user
     * can simply enter the Fixed Price and save.
     */
    async createPricelistForProduct() {
        if (!this.state.product || !this.state.product.id) return;
        const productName = (this.state.product.name || '').trim();
        const defaultName = productName ? (productName + ' - Custom Price') : 'Custom Pricelist';

        this.state.loading = true;
        try {
            // Attempt to create a new pricelist record programmatically
            const newPricelistId = await this.orm.call('product.pricelist', 'create', [{ name: defaultName }]);
            if (!newPricelistId) {
                throw new Error('Failed to create pricelist');
            }

            // Open the pricelist item form to add a rule for this product
            const context = {
                default_pricelist_id: newPricelistId,
                default_applied_on: '1_product',
                default_product_tmpl_id: this.state.product.id,
            };
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: _t('Add Pricelist Rule'),
                res_model: 'product.pricelist.item',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            }, {
                onClose: async () => {
                    // Refresh config to fetch the newly created pricelist
                    await this.loadConfig();
                    this.state.selectedPricelistId = newPricelistId;

                    // Refresh product so any immediate price change is visible
                    const lookupTerm = this.state.product.barcode || this.state.product.default_code || this.state.product.name;
                    if (lookupTerm) this.searchProduct(lookupTerm);
                }
            });
            this.notification.add(_t('Pricelist created: ') + defaultName, { type: 'success' });
        } catch (e) {
            // If creation fails (e.g., required fields like currency_id), open pricelist form as fallback
            this.notification.add(_t('Could not create pricelist automatically. Opening create form.'), { type: 'warning' });
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: _t('Create Pricelist'),
                res_model: 'product.pricelist',
                views: [[false, 'form']],
                target: 'new',
                context: { default_name: defaultName },
            }, {
                onClose: async () => {
                    // Refresh config in case they successfully created it manually
                    await this.loadConfig();
                    const lookupTerm = this.state.product.barcode || this.state.product.default_code || this.state.product.name;
                    if (lookupTerm) this.searchProduct(lookupTerm);
                }
            });
            console.error('[ProductChecker] createPricelistForProduct error', e);
        } finally {
            this.state.loading = false;
        }
    }

    onCostInputKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            this.saveCostUpdate();
        } else if (ev.key === 'Escape') {
            ev.preventDefault();
            this.closeCostUpdateModal();
        }
    }

    onStockInputKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            this.saveStockUpdate();
        } else if (ev.key === 'Escape') {
            ev.preventDefault();
            this.closeStockUpdateModal();
        }
    }

    closeCostUpdateModal() {
        this.state.showCostUpdateModal = false;
    }

    async saveCostUpdate() {
        if (!this.state.product) return;
        this.state.loading = true;
        const newCost = parseFloat(this.state.editCostValue) || 0;
        try {
            const result = await this.orm.call('product.template', 'update_standard_price', [
                this.state.product.id, newCost, this.state.selectedPricelistId || null
            ]);

            if (result.success) {
                // Update product data with fresh_info to re-render Sales Price immediately
                if (result.data) {
                    this.state.product = result.data;
                } else {
                    this.state.product.standard_price = result.new_cost !== undefined ? result.new_cost : newCost;
                }

                this.notification.add(_t("Cost updated successfully"), { type: "success" });
                this.closeCostUpdateModal();
            } else {
                this.notification.add(_t('Failed to update cost: ') + (result.error || 'Unknown error'), { type: "danger" });
            }
        } catch (e) {
            this.notification.add(_t('Failed to update cost: ') + (e.data?.message || e.message || String(e)), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    closeStockUpdateModal() {
        this.state.showStockUpdateModal = false;
    }

    async saveStockUpdate() {
        if (!this.state.product) return;
        this.state.loading = true;
        const newStock = parseFloat(this.state.editStockValue) || 0;
        try {
            const result = await this.orm.call('product.template', 'update_quantity_on_hand', [
                this.state.product.id, newStock
            ]);
            if (result.success) {
                this.state.product.qty_on_hand = result.new_qty;
                this.notification.add(_t("Stock updated successfully"), { type: "success" });
                this.closeStockUpdateModal();
            } else {
                this.notification.add(_t('Failed to update stock: ') + (result.error || 'Unknown error'), { type: "danger" });
            }
        } catch (e) {
            this.notification.add(_t('Error updating stock: ') + (e.data?.message || e.message || String(e)), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    resetSearch() {
        this.state.barcode = "";
        this.state.product = null;
        this.state.notFound = false;
        this.state.searchedCode = "";
        this.state.showCreateForm = false;
        this.focusInput();
    }

    newScan() {
        this.state.barcode = "";
        this.state.notFound = false;
        this.focusInput();
    }

    formatPrice(price, product) {
        if (price === undefined || price === null) return "";
        const symbol = product?.currency_symbol || "";
        const position = product?.currency_position || "before";
        const num = Number(price).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return position === "after" ? `${num} ${symbol}` : `${symbol} ${num}`;
    }

    getProfitInfo(product) {
        if (!product) return { margin: 0, percentage: 0 };
        const price = parseFloat(product.price) || 0;
        const cost = parseFloat(product.standard_price) || 0;
        const margin = price - cost;
        const percentage = price > 0 ? (margin / price) * 100 : 0;
        return { margin, percentage };
    }


    // ================================================================
    // CAMERA BARCODE SCANNER
    // ================================================================
    // Two modes:
    //   - "once":       scan a single barcode, auto-add, close camera
    //   - "continuous": scan repeatedly until user closes, anti-duplicate
    //                   by ignoring same code within 2 seconds
    // Uses native BarcodeDetector API (Chrome Android, Edge, Safari iOS17+)
    // Torch/flash via MediaStreamTrack.applyConstraints({torch: true})
    // ================================================================

    openCameraOnce() {
        this.state.cameraMode = "once";
        this._startCamera();
    }

    openCameraContinuous() {
        this.state.cameraMode = "continuous";
        this._startCamera();
    }

    async _startCamera() {
        // Initialize or resume Web Audio API on user interaction (to bypass browser autoplay policies)
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext && !this._audioCtx) {
                this._audioCtx = new AudioContext();
            }
            if (this._audioCtx && this._audioCtx.state === "suspended") {
                this._audioCtx.resume();
            }
        } catch (_e) {
            // Ignore if audio isn't supported
        }

        this.state.cameraError = null;
        this.state.lastDetected = null;
        this.state.torchSupported = false;
        this.state.torchOn = false;
        this.state.scannedCount = 0;
        this.state.lastScanStatus = null;
        this.state.lastScanMessage = null;
        this._lastScannedCode = null;
        this._lastScannedAt = 0;
        this.state.showCameraModal = true;

        // Load BarcodeDetector polyfill for iOS Safari/Chrome if needed
        const hasBarcodeDetector = await ensureBarcodeDetector();
        if (!hasBarcodeDetector) {
            this.state.cameraError = _t(
                "Your browser does not support the Barcode Detector API. " +
                "Please use Chrome on Android, or use manual input above."
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
            this.state.cameraError = _t("Failed to initialize barcode detector: ") + e.message;
            return;
        }

        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: this.state.cameraFacing },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });
        } catch (e) {
            this.state.cameraError = _t(
                "Cannot access camera: " + (e.message || e) +
                ". Make sure you have granted camera permission."
            );
            return;
        }

        // Wait for DOM to render the video element (modal just opened via showCameraModal = true)
        setTimeout(() => {
            if (!this.cameraVideoRef.el) {
                this.state.cameraError = _t("Video element not ready.");
                this.stopCamera();
                return;
            }

            const videoEl = this.cameraVideoRef.el;
            videoEl.srcObject = this._cameraStream;
            this._cameraTrack = this._cameraStream.getVideoTracks()[0];

            // Samsung Tab S8 (and many Android devices) don't report torch capability
            // until the video is actively playing frames. We listen for the "playing"
            // event before starting the torch-detection polling loop.
            const onVideoPlaying = () => {
                videoEl.removeEventListener("playing", onVideoPlaying);
                this._detectTorchCapability();
            };
            videoEl.addEventListener("playing", onVideoPlaying);

            // Safety fallback: if "playing" never fires within 3 seconds,
            // still try to detect torch (some emulators / special devices).
            setTimeout(() => {
                videoEl.removeEventListener("playing", onVideoPlaying);
                if (!this.state.torchSupported && this._cameraTrack) {
                    this._detectTorchCapability();
                }
            }, 3000);

            this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
        }, 100);
    }


    _detectTorchCapability() {
        // Poll for torch capability. On Samsung Tab S8 and similar devices,
        // getCapabilities() only reports torch after the camera hardware has
        // fully initialised and the video is playing frames.
        let checkAttempts = 0;
        const checkTorch = () => {
            if (this._cameraTrack) {
                let hasTorch = false;
                if (typeof this._cameraTrack.getCapabilities === "function") {
                    const caps = this._cameraTrack.getCapabilities();
                    if (caps && caps.torch) {
                        hasTorch = true;
                    }
                }
                if (!hasTorch && typeof this._cameraTrack.getSettings === "function") {
                    const settings = this._cameraTrack.getSettings();
                    if (settings && "torch" in settings) {
                        hasTorch = true;
                    }
                }
                if (hasTorch) {
                    this.state.torchSupported = true;
                    return;
                }
            }
            checkAttempts++;
            if (checkAttempts < 20 && this.state.showCameraModal) {
                setTimeout(checkTorch, 500); // Check every 500ms for ~10 seconds
            }
        };
        checkTorch();
    }

    async _scanFrame() {
        if (!this._barcodeDetector || !this.cameraVideoRef.el) {
            return;
        }
        const video = this.cameraVideoRef.el;
        if (video.readyState < 2) {
            return;
        }
        try {
            const codes = await this._barcodeDetector.detect(video);
            if (codes && codes.length > 0) {
                const value = codes[0].rawValue;
                if (!value) return;

                // Anti-double-detection guard: ignore the SAME code if
                // detected within 2 seconds of the previous detection.
                // This prevents the camera polling loop from firing the
                // same barcode multiple times in quick succession.
                const now = Date.now();
                if (value === this._lastScannedCode && (now - this._lastScannedAt) < 2000) {
                    return;
                }
                this._lastScannedCode = value;
                this._lastScannedAt = now;
                this.state.lastDetected = value;

                await this._onBarcodeDetected(value);
            }
        } catch (_e) {
            // transient detection errors are ignored
        }
    }

    async _onBarcodeDetected(barcode) {
        // Pause the scan loop while we process this barcode to avoid
        // overlapping RPC calls.
        const wasLoopActive = this._scanLoopHandle !== null;
        if (wasLoopActive) {
            clearInterval(this._scanLoopHandle);
            this._scanLoopHandle = null;
        }

        try {
            // Perform the actual search + add-to-print-list
            const result = await this._scanAndAddToPrintList(barcode);

            // Play the appropriate sound based on the search result
            this._playScanSound(result);

            if (this.state.cameraMode === "once") {
                // Scan Once: close camera after first successful scan
                this.stopCamera();
                this.state.showCameraModal = false;
                return;
            }

            // Continuous mode: show flash feedback, keep camera open
            if (result === "added") {
                this.state.lastScanStatus = "success";
                this.state.lastScanMessage = `Found: ${this.state.product.name}`;
                this.state.scannedCount = this.state.scannedCount + 1;
            } else if (result === "duplicate") {
                this.state.lastScanStatus = "duplicate";
                this.state.lastScanMessage = `Already in list: ${this.state.product.name}`;
            } else {
                this.state.lastScanStatus = "notfound";
                this.state.lastScanMessage = `Not found: ${barcode}`;
            }

            // Clear flash feedback after 1.5s
            setTimeout(() => {
                this.state.lastScanStatus = null;
                this.state.lastScanMessage = null;
            }, 1500);
        } finally {
            // Restart the scan loop in continuous mode
            if (this.state.cameraMode === "continuous" && this.state.showCameraModal) {
                this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
            }
        }
    }


    async _scanAndAddToPrintList(barcode) {
        // Returns: "added" | "duplicate" | "notfound" | "error"
        try {
            const result = await this.orm.call(
                "product.template",
                "search_product_by_barcode",
                [barcode.trim(), this.state.selectedPricelistId]
            );
            if (!result.found) {
                // Product not found. In continuous mode just flash and keep scanning.
                // In once mode, show the "Not Found" card so user can quick-create.
                if (this.state.cameraMode === "once") {
                    this.state.product = null;
                    this.state.notFound = true;
                    this.state.searchedCode = barcode.trim();
                } else {
                    this.notification.add(
                        _t("Product not found: ") + barcode,
                        { type: "warning" }
                    );
                }
                return "notfound";
            }

            // Found. Set as current product and add to history.
            this.state.product = result.data;
            this.state.metaCategQuery = result.data.categ_name || "";
            this.state.metaCategSuggestions = [];
            this.state.metaCategActiveSuggestion = -1;
            this.state.showMetaCategDropdown = false;
            this.state.notFound = false;
            this.state.showCreateForm = false;
            this.addToHistory(result.data);

            // Add to print list (silent mode — no toast, we show our own feedback)
            const addResult = await this.addToPrintList(true);
            if (addResult && addResult.success) {
                if (addResult.already_exists) {
                    this.notification.add(
                        _t("Already in print list: ") + result.data.name,
                        { type: "info" }
                    );
                    return "duplicate";
                }
                return "added";
            }
            return "error";
        } catch (error) {
            this.notification.add(
                _t("Scan error: ") + (error.message || error),
                { type: "danger" }
            );
            return "error";
        }
    }

    async toggleTorch() {
        if (!this._cameraTrack || !this.state.torchSupported) {
            return;
        }
        const newState = !this.state.torchOn;
        try {
            await this._cameraTrack.applyConstraints({
                advanced: [{ torch: newState }],
            });
            this.state.torchOn = newState;
        } catch (e) {
            this.notification.add(
                _t("Could not toggle flash: ") + (e.message || e),
                { type: "warning" }
            );
        }
    }

    async switchCamera() {
        // Toggle between back ("environment") and front ("user") camera
        this.state.cameraFacing =
            this.state.cameraFacing === "environment" ? "user" : "environment";

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
        this.state.torchOn = false;
        this.state.torchSupported = false;

        // Restart camera with the new facing mode
        try {
            this._cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: this.state.cameraFacing },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });
        } catch (e) {
            this.state.cameraError = _t(
                "Cannot switch camera: " + (e.message || e)
            );
            return;
        }

        if (this.cameraVideoRef.el) {
            const videoEl = this.cameraVideoRef.el;
            videoEl.srcObject = this._cameraStream;
            this._cameraTrack = this._cameraStream.getVideoTracks()[0];

            // Wait for video to start playing before detecting torch
            const onVideoPlaying = () => {
                videoEl.removeEventListener("playing", onVideoPlaying);
                this._detectTorchCapability();
            };
            videoEl.addEventListener("playing", onVideoPlaying);

            setTimeout(() => {
                videoEl.removeEventListener("playing", onVideoPlaying);
                if (!this.state.torchSupported && this._cameraTrack) {
                    this._detectTorchCapability();
                }
            }, 3000);

            this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
        }
    }

    async closeCameraScanner() {
        await this.stopCamera();
        this.state.showCameraModal = false;
    }

    async stopCamera() {
        if (this._scanLoopHandle) {
            clearInterval(this._scanLoopHandle);
            this._scanLoopHandle = null;
        }
        if (this._cameraTrack && this.state.torchOn) {
            try {
                await this._cameraTrack.applyConstraints({ advanced: [{ torch: false }] });
            } catch (_e) { /* ignore */ }
        }
        if (this._cameraStream) {
            this._cameraStream.getTracks().forEach(t => t.stop());
            this._cameraStream = null;
        }
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this.state.torchOn = false;
        this.state.torchSupported = false;
    }

    // ============================================================
    // PRODUCT LIST — Left-side drawer
    // Desktop-only (hidden on mobile via SCSS).
    // Search filter is preserved across close/open cycles.
    // ============================================================

    /**
     * Toggle the left-side Product List drawer. First open triggers the
     * initial data load; subsequent toggles just show/hide without refetch.
     * Also loads the user's saved filters on first open and auto-applies
     * the one flagged as default (if any).
     */
    async toggleProductList() {
        this.state.productListOpen = !this.state.productListOpen;
        if (this.state.productListOpen && !this.state.productListInitialized) {
            // Load saved filters first so we can auto-apply the default one
            // BEFORE making the initial product list RPC.
            if (!this.state.savedFiltersLoaded) {
                await this.loadSavedFilters({ applyDefault: true });
            }
            this.loadProductList(true);
        }
    }

    /**
     * Close the drawer WITHOUT resetting the search filter or loaded items,
     * so re-opening restores the previous state instantly.
     */
    closeProductList() {
        this.state.productListOpen = false;
    }

    /**
     * Debounced handler for the filter input inside the drawer.
     * Resets the list to the first page with the new query.
     */
    onProductListQueryInput(ev) {
        this.state.productListQuery = ev.target.value;
        if (this._productListDebounceTimer) {
            clearTimeout(this._productListDebounceTimer);
        }
        this._productListDebounceTimer = setTimeout(() => {
            this.loadProductList(true);
        }, 300);
    }

    /**
     * Fetch a page of products from the backend.
     *
     * @param {boolean} reset - If true, offset is reset to 0 and the current
     *                          list is replaced. If false, new items are
     *                          appended (used by "Load More").
     */
    async loadProductList(reset = false) {
        if (reset) {
            this.state.productListOffset = 0;
            this.state.productListItems = [];
            this.state.productListTotal = 0;
        }
        this.state.productListLoading = true;
        try {
            const result = await this.orm.call(
                "product.template",
                "search_products_for_panel",
                [],
                {
                    query: this.state.productListQuery || "",
                    pricelist_id: this.state.selectedPricelistId || false,
                    offset: this.state.productListOffset,
                    limit: 50,
                    filter_domain: this.state.productListDomain || "[]",
                }
            );
            const items = result.products || [];
            if (reset) {
                this.state.productListItems = items;
            } else {
                this.state.productListItems = this.state.productListItems.concat(items);
            }
            this.state.productListTotal = result.total || 0;
            this.state.productListFilterCount = result.filter_count || 0;
            this.state.productListOffset = this.state.productListItems.length;
            this.state.productListInitialized = true;
        } catch (error) {
            this.notification.add(
                _t("Failed to load product list: ") + (error.message || String(error)),
                { type: "danger" }
            );
        } finally {
            this.state.productListLoading = false;
        }
    }

    /**
     * Append the next page of products to the current list.
     */
    async loadMoreProducts() {
        if (this.state.productListLoading) return;
        if (this.state.productListItems.length >= this.state.productListTotal) return;
        await this.loadProductList(false);
    }

    /**
     * Click handler for a product row in the drawer: loads that product into
     * the main display area by reusing the normal search flow. The drawer
     * stays OPEN so the user can click another product right after.
     */
    onProductListItemClick(item) {
        if (!item) return;
        const searchTerm = item.barcode || item.default_code || item.name;
        if (!searchTerm) return;
        this.searchProduct(searchTerm);
        if (window.innerWidth <= 768) {
            this.closeProductList();
        }
    }

    // ============================================================
    // CUSTOM FILTER — Domain Selector dialog
    // ============================================================

    /**
     * Open Odoo's built-in Domain Selector dialog so users can build
     * complex filter rules.
     *
     * Defensive implementation — Odoo 18 has different prop names across
     * minor versions (`onConfirm`, `onSelected`, or even `onClose`). We
     * register every callback we've seen in the wild so the dialog works
     * regardless of version. The first one that fires will invoke the
     * shared `_applyFilterDomain` helper.
     */
    openFilterDialog() {
        // Guard so only ONE of the callbacks actually applies the domain
        // (Odoo sometimes fires both onSelected + onClose sequentially).
        let applied = false;
        const apply = (newDomain) => {
            if (applied) return;
            applied = true;
            this._applyFilterDomain(newDomain);
        };

        this.dialog.add(DomainSelectorDialog, {
            resModel: "product.template",
            domain: this.state.productListDomain || "[]",
            isDebugMode: false,
            onConfirm: apply,
        });
    }

    /**
     * Normalise the domain returned by DomainSelectorDialog (may be a
     * string, an array, or an object depending on Odoo version) into a
     * Python-literal string the backend can safe_eval, then reload.
     */
    _applyFilterDomain(newDomain) {
        // Debug trace — helps diagnose why a built filter might not apply.
        // Keep this log while the feature stabilises.
        console.log("[ProductChecker] Filter callback fired:", newDomain,
            "(type:", typeof newDomain, ", isArray:",
            Array.isArray(newDomain), ")");

        // Dialog dismissed with no domain (Escape / backdrop click) — no-op.
        if (newDomain === undefined || newDomain === null) {
            return;
        }

        let domainStr = "[]";
        if (typeof newDomain === "string") {
            domainStr = newDomain || "[]";
        } else if (Array.isArray(newDomain)) {
            // Serialise the list back to a Python-literal string so the
            // backend `safe_eval` can parse it uniformly.
            domainStr = JSON.stringify(newDomain)
                .replace(/true/g, "True")
                .replace(/false/g, "False")
                .replace(/null/g, "None");
        } else if (typeof newDomain === "object") {
            // Some versions wrap the result: {domain: "..."} or pass back
            // the full tree-node object { type: "...", children: [...] }.
            if (typeof newDomain.domain === "string") {
                domainStr = newDomain.domain || "[]";
            } else {
                // Last resort — stringify whatever we got.
                try {
                    domainStr = JSON.stringify(newDomain)
                        .replace(/true/g, "True")
                        .replace(/false/g, "False")
                        .replace(/null/g, "None");
                } catch (_e) {
                    domainStr = "[]";
                }
            }
        }

        console.log("[ProductChecker] Applying domain string:", domainStr);
        this.state.productListDomain = domainStr;
        this.loadProductList(true);
    }

    /**
     * Remove all filter rules. Triggered from the "Clear" button in the
     * chip summary at the bottom of the drawer.
     */
    clearFilterDomain() {
        this.state.productListDomain = "[]";
        this.state.productListFilterCount = 0;
        this.loadProductList(true);
    }

    /**
     * Clear BOTH text query and domain filter, then reload. Called from
     * the "Clear all filters" button that appears in the empty state
     * when a filter returns zero products.
     */
    clearAllFiltersAndQuery() {
        this.state.productListDomain = "[]";
        this.state.productListFilterCount = 0;
        this.state.productListQuery = "";
        this.state.activeSavedFilterId = null;
        this.loadProductList(true);
    }

    // ============================================================
    // INLINE PRODUCT FIELD TOGGLES
    // Auto-save on change. On failure for is_storable=true, open the
    // Track Inventory recovery modal (Duplicate & Archive flow).
    // ============================================================

    async onProductFieldToggle(fieldName, ev) {
        if (!this.state.product) return;

        const newValue = !!(ev && ev.target && ev.target.checked);
        const oldValue = !!this.state.product[fieldName];

        // Optimistic UI: reflect the new value immediately.
        this.state.product[fieldName] = newValue;
        this.state.savingOptionField = fieldName;

        try {
            const result = await this.orm.call(
                "product.template",
                "toggle_product_field",
                [this.state.product.id, fieldName, newValue]
            );

            if (result && result.success) {
                this.notification.add(_t("Saved"), { type: "success" });
                return;
            }

            // Failed — revert optimistic change.
            this.state.product[fieldName] = oldValue;
            if (ev && ev.target) ev.target.checked = oldValue;

            if (result && result.is_track_inventory) {
                // Track Inventory conflict — offer Duplicate & Archive recovery.
                this.state.trackInventoryErrorMessage = (result.error || _t("Unknown error")).toString();
                this.state.showTrackInventoryErrorModal = true;
            } else {
                this.notification.add(
                    _t("Cannot update: ") + ((result && result.error) || _t("unknown error")),
                    { type: "danger" }
                );
            }
        } catch (error) {
            // Revert on RPC exception.
            this.state.product[fieldName] = oldValue;
            if (ev && ev.target) ev.target.checked = oldValue;
            this.notification.add(
                _t("Error: ") + (error.message || String(error)),
                { type: "danger" }
            );
        } finally {
            this.state.savingOptionField = null;
        }
    }

    closeTrackInventoryErrorModal() {
        this.state.showTrackInventoryErrorModal = false;
        this.state.trackInventoryErrorMessage = "";
    }

    /**
     * Track Inventory recovery flow: create a duplicate of the current
     * product with is_storable=true (moving barcode + default_code to the
     * new product), archive the original, then load the new product.
     */
    async duplicateAndArchive() {
        if (!this.state.product || !this.state.product.id) return;

        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "product.template",
                "duplicate_for_track_inventory",
                [this.state.product.id, this.state.selectedPricelistId || false]
            );

            if (result && result.success && result.data) {
                this.state.product = result.data;
                this.state.metaCategQuery = result.data.categ_name || "";
                this.state.metaCategSuggestions = [];
                this.state.metaCategActiveSuggestion = -1;
                this.state.showMetaCategDropdown = false;
                this.addToHistory(result.data);
                this.state.showTrackInventoryErrorModal = false;
                this.state.trackInventoryErrorMessage = "";
                this.notification.add(
                    _t("New product created with Track Inventory enabled. Original archived."),
                    { type: "success" }
                );
            } else {
                this.notification.add(
                    _t("Duplicate failed: ") + ((result && result.error) || _t("unknown error")),
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(
                _t("Error during duplicate: ") + (error.message || String(error)),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    // ============================================================
    // SAVED FAVORITES (Saved Searches)
    // Per-user saved combos of text query + domain. Optional default
    // auto-applies the next time the drawer is opened.
    // ============================================================

    /**
     * Load the current user's saved filters from the backend.
     *
     * @param {Object} opts
     * @param {boolean} opts.applyDefault - If true and a default filter
     *        exists, apply it immediately to the drawer state (without
     *        triggering a product reload; caller is responsible for that).
     */
    async loadSavedFilters({ applyDefault = false } = {}) {
        try {
            const filters = await this.orm.call(
                "andykanoz_product_checker.saved_filter",
                "get_saved_filters",
                []
            );
            this.state.savedFilters = filters || [];
            this.state.savedFiltersLoaded = true;

            if (applyDefault) {
                const def = this.state.savedFilters.find((f) => f.is_default);
                if (def) {
                    this.state.productListDomain = def.domain || "[]";
                    this.state.productListQuery = def.query || "";
                    this.state.activeSavedFilterId = def.id;
                }
            }
        } catch (error) {
            this.notification.add(
                _t("Failed to load saved filters: ") + (error.message || String(error)),
                { type: "danger" }
            );
        }
    }

    /**
     * Toggle visibility of the Favorites dropdown panel.
     * Always closes the inline save form when the menu is opened fresh.
     */
    async toggleFavoritesDropdown() {
        const willOpen = !this.state.favoritesDropdownOpen;
        this.state.favoritesDropdownOpen = willOpen;
        if (willOpen) {
            // Refresh every time the menu opens — cheap, and ensures we
            // see favorites created from another browser tab.
            await this.loadSavedFilters({ applyDefault: false });
            this.state.saveFilterFormOpen = false;
        }
    }

    /**
     * Toggle the "Save current search" accordion form inside the dropdown.
     * When opening, pre-fill the name input with the active favorite's
     * name (if any) so the user can easily overwrite it.
     */
    toggleSaveFilterForm() {
        this.state.saveFilterFormOpen = !this.state.saveFilterFormOpen;
        if (this.state.saveFilterFormOpen) {
            if (this.state.activeSavedFilterId) {
                const active = this.state.savedFilters.find(
                    (f) => f.id === this.state.activeSavedFilterId
                );
                if (active) {
                    this.state.saveFilterName = active.name;
                    this.state.saveFilterIsDefault = !!active.is_default;
                    return;
                }
            }
            this.state.saveFilterName = "";
            this.state.saveFilterIsDefault = false;
        }
    }

    /** Enter inside the name input submits the save. */
    onSaveFilterNameKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            if ((this.state.saveFilterName || "").trim()) {
                this.saveCurrentFilter();
            }
        }
    }

    /**
     * Persist the current drawer text query + domain as a named favorite.
     * If a filter with the same name already exists it is overwritten.
     */
    async saveCurrentFilter() {
        const name = (this.state.saveFilterName || "").trim();
        if (!name) {
            this.notification.add(_t("Name is required"), { type: "warning" });
            return;
        }

        try {
            const result = await this.orm.call(
                "andykanoz_product_checker.saved_filter",
                "save_current_filter",
                [],
                {
                    name: name,
                    domain: this.state.productListDomain || "[]",
                    query: this.state.productListQuery || "",
                    is_default: !!this.state.saveFilterIsDefault,
                }
            );

            if (result && result.success && result.filter) {
                this.notification.add(
                    _t("Filter saved: ") + result.filter.name,
                    { type: "success" }
                );
                this.state.activeSavedFilterId = result.filter.id;
                this.state.saveFilterFormOpen = false;
                this.state.saveFilterName = "";
                this.state.saveFilterIsDefault = false;
                // Reload the list so default flags and ordering are correct.
                await this.loadSavedFilters({ applyDefault: false });
            } else {
                this.notification.add(
                    _t("Failed to save filter: ") +
                    ((result && result.error) || _t("unknown error")),
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(
                _t("Error: ") + (error.message || String(error)),
                { type: "danger" }
            );
        }
    }

    /**
     * Apply a saved favorite: restore its text query + domain, then reload
     * the product list from page 1. Closes the dropdown for clarity.
     */
    async applySavedFilter(filter) {
        if (!filter) return;
        this.state.productListDomain = filter.domain || "[]";
        this.state.productListQuery = filter.query || "";
        this.state.activeSavedFilterId = filter.id;
        this.state.favoritesDropdownOpen = false;
        this.state.saveFilterFormOpen = false;
        await this.loadProductList(true);
    }

    /**
     * Delete a saved favorite. If it was the currently active one, clear
     * the active marker (but leave the applied domain in place so the
     * user doesn't lose context).
     */
    async deleteSavedFilter(filter) {
        if (!filter) return;
        try {
            await this.orm.call(
                "andykanoz_product_checker.saved_filter",
                "delete_saved_filter",
                [filter.id]
            );
            this.state.savedFilters = this.state.savedFilters.filter(
                (f) => f.id !== filter.id
            );
            if (this.state.activeSavedFilterId === filter.id) {
                this.state.activeSavedFilterId = null;
            }
            this.notification.add(
                _t("Filter deleted: ") + filter.name,
                { type: "info" }
            );
        } catch (error) {
            this.notification.add(
                _t("Failed to delete filter: ") + (error.message || String(error)),
                { type: "danger" }
            );
        }
    }

    /**
     * Show large image detail in modal/backdrop when user clicks the product image.
     */
    viewProductImage() {
        if (!this.state.product || !this.state.product.image_url) {
            this.notification.add(_t('No image available'), { type: 'warning' });
            return;
        }
        // Use the product image URL (bypass cache timestamp if present)
        this.state.imageDetailUrl = this.state.product.image_url;
        this.state.imageDetailOpen = true;
    }

    closeImageDetail() {
        this.state.imageDetailOpen = false;
        this.state.imageDetailUrl = null;
    }
}

registry.category("actions").add(
    "andykanoz_product_checker.ProductCheckerAction",
    ProductCheckerAction
);
