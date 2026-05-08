/** @odoo-module **/

/**
 * andykanoz_quick_purchase
 * ------------------------
 * OWL component for scanner-driven, single-vendor purchase entry.
 */

import { Component, useState, useRef, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const QP_ACTIVE_SESSION_KEY = "andykanoz_quick_purchase_active";

export class QuickPurchase extends Component {
    static template = "andykanoz_quick_purchase.QuickPurchase";
    static props = ["*"];

    _t = _t;

    setup() {
        this.action = useService("action");

        // Debug: capture all unhandled errors so we can see the REAL error
        // instead of the secondary formatTraceback error
        if (!window._qpDebugAttached) {
            window.addEventListener("unhandledrejection", (ev) => {
                console.error("[QP-DEBUG] Unhandled rejection:", ev.reason);
                if (ev.reason && ev.reason.stack) {
                    console.error("[QP-DEBUG] Stack:", ev.reason.stack);
                }
                if (ev.reason && ev.reason.message) {
                    console.error("[QP-DEBUG] Message:", ev.reason.message);
                }
            });
            window.addEventListener("error", (ev) => {
                console.error("[QP-DEBUG] Window error:", ev.error || ev.message);
                if (ev.error && ev.error.stack) {
                    console.error("[QP-DEBUG] Stack:", ev.error.stack);
                }
            });
            window._qpDebugAttached = true;
            console.log("[QP-DEBUG] Error listeners attached");
        }

        this.notification = useService("notification");
        this.scanInputRef = useRef("scanInput");
        this.newProductNameRef = useRef("newProductName");
        this.cameraVideoRef = useRef("cameraVideo");

        // Camera internals (not reactive)
        this._cameraStream = null;
        this._cameraTrack = null;
        this._barcodeDetector = null;
        this._scanLoopHandle = null;

        // Audio context for scan beep sounds
        this._audioCtx = null;

        // Anti-duplicate guard for continuous scanning
        this._lastScannedCode = null;
        this._lastScannedAt = 0;

        // Session save debounce handle
        this._saveSessionHandle = null;

        this.state = useState({
            sessions: [],
            activeSessionId: null,
            editingSessionName: null,
            editingSessionNameValue: "",

            partnerId: null,
            partnerName: "",
            vendorQuery: "",
            vendorSuggestions: [],
            vendorActiveSuggestion: -1,
            vendorDebounceHandle: null,
            showVendorDropdown: false,

            scanQuery: "",
            suggestions: [],
            activeSuggestion: -1,
            showNoResult: false,
            lastSearched: "",
            searchDebounceHandle: null,

            lines: [],
            creating: false,

            showCreateModal: false,
            creatingProduct: false,
            metadata: { categories: [], uoms: [], public_categories: [] },
            newProduct: {
                name: "", barcode: "", default_code: "",
                cost: 0, categ_id: null, categ_name: "",
                public_categ_ids: [],
                is_storable: false,
                available_in_pos: false,
                is_published: false,
            },

            // Category autocomplete (inside Quick Create modal)
            categQuery: "",
            categSuggestions: [],
            categActiveSuggestion: -1,
            showCategDropdown: false,

            // Public category multi-select autocomplete
            publicCategQuery: "",
            publicCategSuggestions: [],
            publicCategActiveSuggestion: -1,
            showPublicCategDropdown: false,

            // Camera scanner state
            showCameraModal: false,
            cameraMode: "once",              // "once" or "continuous"
            cameraError: null,
            lastDetected: null,
            torchSupported: false,
            torchOn: false,
            scannedCount: 0,                 // Counter in continuous mode
            lastScanStatus: null,            // "success" | "duplicate" | "notfound"
            lastScanMessage: null,           // Toast message for feedback

            // Session draft status indicator
            sessionStatus: null,             // null | "saving" | "saved" | "error" | "loaded"

            // Duplicate scan confirmation modal (Once mode only)
            showDuplicateModal: false,
            duplicateProduct: null,          // product object from scan
            duplicateExistingLine: null,     // reference to the existing line in state.lines
            duplicateAddQty: 1,              // qty to add (default 1, min 1)
        });

        onWillStart(async () => {
            await this.loadMetadata();
            await this._loadSessions();
        });

        onMounted(() => {
            this.focusScanInput();
        });

        onWillUnmount(() => {
            this.stopCamera();
            // Flush any pending debounced save and force an immediate save
            // so the draft is not lost when navigating away.
            if (this._saveSessionHandle) {
                clearTimeout(this._saveSessionHandle);
                this._saveSessionHandle = null;
            }
            if (this.state.activeSessionId && this.state.sessions.length > 0) {
                this._saveCurrentSession();
                // _saveCurrentSession debounces; flush immediately
                if (this._saveSessionHandle) {
                    clearTimeout(this._saveSessionHandle);
                    this._saveSessionHandle = null;
                }
                this._saveSessionToServer();
            }
        });
    }


    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------

    async loadMetadata() {
        try {
            const meta = await rpc("/andykanoz_quick_purchase/form_metadata", {});
            this.state.metadata = meta || { categories: [], uoms: [], public_categories: [] };
            if (!this.state.metadata.public_categories) {
                this.state.metadata.public_categories = [];
            }
        } catch (e) {
            console.warn("Quick Purchase: failed to load metadata", e);
        }
    }

    // ------------------------------------------------------------------
    // Session persistence (Server Side)
    // ------------------------------------------------------------------

    _generateSessionId() {
        return "qp_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    }

    async _loadSessions() {
        this.state.sessionStatus = "loading";
        try {
            const serverSessions = await rpc("/andykanoz_quick_purchase/load_sessions", {});

            if (serverSessions && serverSessions.length > 0) {
                this.state.sessions = serverSessions;

                // Keep the active session locally for UX (which tab is currently opened)
                const localActiveId = localStorage.getItem(QP_ACTIVE_SESSION_KEY);
                let sessionToRestore = serverSessions[0].id;

                if (localActiveId && serverSessions.find(s => s.id === localActiveId)) {
                    sessionToRestore = localActiveId;
                }

                this._restoreSession(sessionToRestore);
                this.state.sessionStatus = "loaded";
            } else {
                // No saved sessions — create the first one
                this._createNewSession(false);
                this.state.sessionStatus = null;
            }

            // Check if opened from PO button with initialization data
            if (this.props.action && this.props.action.params && this.props.action.params.init_lines) {
                const p = this.props.action.params;
                this._createNewSession(true, {
                    name: p.init_po_name || "New PO Draft",
                    partnerId: p.init_partner_id || null,
                    partnerName: p.init_partner_name || "",
                    lines: p.init_lines || []
                });
                // Remove it so it doesn't trigger again on component remount
                delete this.props.action.params.init_lines;
            }
        } catch (e) {
            console.warn("[QP] Failed to load sessions from server:", e);
            this._createNewSession(false);
            this.state.sessionStatus = "error";
        }
    }

    _restoreSession(sessionId) {
        const session = this.state.sessions.find(s => s.id === sessionId);
        if (!session) return;

        this.state.activeSessionId = session.id;
        this.state.partnerId = session.partnerId || null;
        this.state.partnerName = session.partnerName || "";
        this.state.vendorQuery = session.partnerName || "";
        this.state.lines = session.lines ? JSON.parse(JSON.stringify(session.lines)) : [];
        this.state.scanQuery = "";
        this.state.suggestions = [];
        this.state.showNoResult = false;
        this.state.activeSuggestion = -1;

        // Remember last open tab
        localStorage.setItem(QP_ACTIVE_SESSION_KEY, sessionId);
    }

    _saveCurrentSession() {
        if (!this.state.activeSessionId) return;

        const sessions = this.state.sessions;
        const idx = sessions.findIndex(s => s.id === this.state.activeSessionId);
        if (idx < 0) return;

        sessions[idx].partnerId = this.state.partnerId;
        sessions[idx].partnerName = this.state.partnerName;
        sessions[idx].lines = JSON.parse(JSON.stringify(this.state.lines));

        // Auto-name: if name is default and vendor is selected, use vendor name
        if (sessions[idx].name.startsWith("Draft #") && this.state.partnerName) {
            sessions[idx].name = this.state.partnerName;
        }

        this._debounceSaveSession();
    }

    _createNewSession(switchActive = true, initialData = null) {
        if (this.state.sessions.length >= 10) {
            this.notification.add(_t("Maximum of 10 draft sessions reached. Please delete some before creating more."), { type: "warning" });
            return;
        }

        // Find the lowest available number from 1 to 10
        let availableNum = 1;
        const usedNums = new Set();
        for (const s of this.state.sessions) {
            const m = s.name.match(/^Draft #(\d+)$/);
            if (m) {
                usedNums.add(parseInt(m[1]));
            }
        }
        while (usedNums.has(availableNum)) {
            availableNum++;
        }

        const name = initialData && initialData.name ? initialData.name : ("Draft #" + availableNum);

        const newSession = {
            id: this._generateSessionId(),
            name: name,
            partnerId: initialData && initialData.partnerId ? initialData.partnerId : null,
            partnerName: initialData && initialData.partnerName ? initialData.partnerName : "",
            lines: initialData && initialData.lines ? initialData.lines : [],
        };
        this.state.sessions.push(newSession);

        if (switchActive || this.state.sessions.length === 1) {
            this._restoreSession(newSession.id);
        } else {
            this._debounceSaveSession();
        }
    }

    // Proxy for XML template to call
    createNewSession() {
        this._createNewSession(true);
    }

    switchSession(sessionId) {
        if (this.state.activeSessionId === sessionId) return;
        this._saveCurrentSession();
        this._restoreSession(sessionId);
    }

    deleteSession(sessionId) {
        this._deleteSession(sessionId);
    }

    startEditSessionName(sessionId) {
        const session = this.state.sessions.find(s => s.id === sessionId);
        if (session) {
            this.state.editingSessionName = sessionId;
            this.state.editingSessionNameValue = session.name;
        }
    }

    onSessionNameInput(ev) {
        this.state.editingSessionNameValue = ev.target.value;
    }

    onSessionNameKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.saveSessionName();
        } else if (ev.key === "Escape") {
            this.state.editingSessionName = null;
        }
    }

    saveSessionName() {
        if (!this.state.editingSessionName) return;

        const idx = this.state.sessions.findIndex(s => s.id === this.state.editingSessionName);
        if (idx >= 0) {
            const newName = this.state.editingSessionNameValue.trim();
            if (newName) {
                this.state.sessions[idx].name = newName;
                this._debounceSaveSession();
            }
        }
        this.state.editingSessionName = null;
    }

    sortedLines() {
        // Returns the lines as they are (most recently added should be at top based on addProduct logic)
        return this.state.lines || [];
    }

    getSessionSummary(session) {
        if (!session) return "Empty";
        const lines = session.lines || [];
        if (lines.length === 0) return "Empty";

        const totalQty = lines.reduce((sum, l) => sum + (parseFloat(l.qty) || 0), 0);
        let vendor = session.partnerName || "";
        if (!vendor && session.name && session.name !== "New Draft" && !session.name.startsWith("Draft #")) {
            vendor = session.name;
        }

        let summary = `${lines.length} lines, ${totalQty} items`;
        if (vendor) {
            summary += ` for ${vendor}`;
        }
        return summary;
    }

    _deleteSession(sessionId) {
        const idx = this.state.sessions.findIndex(s => s.id === sessionId);
        if (idx < 0) return;

        this.state.sessions.splice(idx, 1);

        if (this.state.activeSessionId === sessionId) {
            if (this.state.sessions.length > 0) {
                // switch to the nearest left tab, or right if it was the first  
                const newIdx = Math.max(0, idx - 1);
                this._restoreSession(this.state.sessions[newIdx].id);
            } else {
                // No sessions left. Just clear the active state instead of making a new one.
                this.state.activeSessionId = null;
                this.state.partnerId = null;
                this.state.partnerName = "";
                this.state.vendorQuery = "";
                this.state.lines = [];
                localStorage.removeItem(QP_ACTIVE_SESSION_KEY);
            }
        }

        // Remove from server
        rpc("/andykanoz_quick_purchase/clear_session", { session_id: sessionId }).catch(e => console.warn(e));

        this._debounceSaveSession();
    }

    _persistSessions() {
        // Obsolete function locally, kept for signature but points to save
        this._debounceSaveSession();
    }

    async _saveSessionToServer() {
        this.state.sessionStatus = "saving";
        try {
            await rpc("/andykanoz_quick_purchase/sync_sessions", {
                sessions: this.state.sessions,
                active_session_id: this.state.activeSessionId
            });
            this.state.sessionStatus = "saved";

            // Keep localActiveId up to date
            if (this.state.activeSessionId) {
                localStorage.setItem(QP_ACTIVE_SESSION_KEY, this.state.activeSessionId);
            }
        } catch (e) {
            console.warn("Quick Purchase: failed to sync sessions to server", e);
            this.state.sessionStatus = "error";
            this.notification.add(
                _t("Failed to save draft session to server!"),
                { type: "danger", sticky: false }
            );
        }
    }

    _debounceSaveSession() {
        if (this._saveSessionHandle) {
            clearTimeout(this._saveSessionHandle);
        }
        this.state.sessionStatus = "saving";
        this._saveSessionHandle = setTimeout(() => {
            this._saveSessionToServer();
        }, 800);
    }

    // ------------------------------------------------------------------
    // Vendor selection
    // ------------------------------------------------------------------

    // ------------------------------------------------------------------
    // Custom vendor autocomplete (replaces Many2XAutocomplete)
    // ------------------------------------------------------------------

    onVendorInput(ev) {
        const query = ev.target.value;
        this.state.vendorQuery = query;
        if (this.state.vendorDebounceHandle) {
            clearTimeout(this.state.vendorDebounceHandle);
        }
        if (!query || query.length < 1) {
            // Empty query: load all vendors (limited)
            this.state.vendorDebounceHandle = setTimeout(() => {
                this.searchVendors("");
            }, 200);
            return;
        }
        this.state.vendorDebounceHandle = setTimeout(() => {
            this.searchVendors(query);
        }, 250);
    }

    onVendorFocus() {
        this.state.showVendorDropdown = true;
        // Preload list on first focus
        if (this.state.vendorSuggestions.length === 0) {
            this.searchVendors("");
        }
    }

    onVendorBlur() {
        // Delay so click on suggestion can register before dropdown closes
        setTimeout(() => {
            this.state.showVendorDropdown = false;
        }, 200);
    }

    onVendorKeydown(ev) {
        const list = this.state.vendorSuggestions;
        if (ev.key === "ArrowDown" && list.length > 0) {
            ev.preventDefault();
            this.state.vendorActiveSuggestion = Math.min(
                this.state.vendorActiveSuggestion + 1,
                list.length - 1
            );
            return;
        }
        if (ev.key === "ArrowUp" && list.length > 0) {
            ev.preventDefault();
            this.state.vendorActiveSuggestion = Math.max(
                this.state.vendorActiveSuggestion - 1, 0
            );
            return;
        }
        if (ev.key === "Enter" && this.state.vendorActiveSuggestion >= 0) {
            ev.preventDefault();
            this.selectVendor(list[this.state.vendorActiveSuggestion]);
            return;
        }
        if (ev.key === "Escape") {
            this.state.showVendorDropdown = false;
            this.state.vendorActiveSuggestion = -1;
        }
    }

    async searchVendors(query) {
        try {
            const vendors = await rpc("/andykanoz_quick_purchase/get_vendors", {
                query: query || null,
                limit: 30,
            });
            this.state.vendorSuggestions = vendors || [];
            this.state.vendorActiveSuggestion = vendors && vendors.length > 0 ? 0 : -1;
        } catch (e) {
            console.error("[QuickPurchase] Vendor search failed:", e);
            this.state.vendorSuggestions = [];
        }
    }

    selectVendor(vendor) {
        if (!vendor || !vendor.id) return;
        if (this.state.lines.length > 0 && vendor.id !== this.state.partnerId) {
            this.notification.add(
                _t("Reset the session before changing vendor."),
                { type: "warning" }
            );
            return;
        }
        this.state.partnerId = vendor.id;
        this.state.partnerName = vendor.name;
        this.state.vendorQuery = vendor.name;
        this.state.showVendorDropdown = false;
        this.state.vendorSuggestions = [];
        this.state.vendorActiveSuggestion = -1;
        this.focusScanInput();
        this._debounceSaveSession();
    }

    onReset() {
        if (this.state.lines.length > 0) {
            if (!confirm(_t("Discard all lines and start a new session?"))) {
                return;
            }
        }
        this.state.partnerId = null;
        this.state.partnerName = "";
        this.state.vendorQuery = "";
        this.state.vendorSuggestions = [];
        this.state.showVendorDropdown = false;
        this.state.vendorActiveSuggestion = -1;
        this.state.lines = [];
        this.state.scanQuery = "";
        this.state.suggestions = [];
        this.state.showNoResult = false;
        this.state.lastSearched = "";
        this.state.activeSuggestion = -1;
        this.state.sessionStatus = null;
        // Clear session on server
        rpc("/andykanoz_quick_purchase/clear_session", {}).catch(() => { });
    }


    // ------------------------------------------------------------------
    // Scan input behavior
    // ------------------------------------------------------------------

    focusScanInput() {
        // Don't focus scan input while camera modal is open (prevents keyboard on mobile)
        if (this.state.showCameraModal) return;
        setTimeout(() => {
            if (this.scanInputRef.el && !this.state.showCameraModal) {
                this.scanInputRef.el.focus();
                this.scanInputRef.el.select();
            }
        }, 50);
    }

    onScanInput(ev) {
        const query = ev.target.value;
        if (this.state.searchDebounceHandle) {
            clearTimeout(this.state.searchDebounceHandle);
        }
        if (!query || query.length < 2) {
            this.state.suggestions = [];
            this.state.showNoResult = false;
            return;
        }
        this.state.searchDebounceHandle = setTimeout(() => {
            this.runSearch(query, false);
        }, 250);
    }

    async onScanKeydown(ev) {
        if (ev.key === "ArrowDown" && this.state.suggestions.length > 0) {
            ev.preventDefault();
            this.state.activeSuggestion = Math.min(
                this.state.activeSuggestion + 1,
                this.state.suggestions.length - 1
            );
            return;
        }
        if (ev.key === "ArrowUp" && this.state.suggestions.length > 0) {
            ev.preventDefault();
            this.state.activeSuggestion = Math.max(this.state.activeSuggestion - 1, 0);
            return;
        }
        if (ev.key === "Escape") {
            this.state.suggestions = [];
            this.state.showNoResult = false;
            this.state.activeSuggestion = -1;
            return;
        }
        if (ev.key === "Enter") {
            ev.preventDefault();
            if (this.state.activeSuggestion >= 0
                && this.state.suggestions[this.state.activeSuggestion]) {
                this.addProduct(this.state.suggestions[this.state.activeSuggestion]);
                return;
            }
            const query = this.state.scanQuery;
            if (query && query.trim()) {
                await this.runSearch(query.trim(), true);
            }
        }
    }

    async runSearch(query, autoAdd) {
        console.log("[QP-DEBUG] runSearch called:", { query, autoAdd, partnerId: this.state.partnerId });
        try {
            const result = await rpc("/andykanoz_quick_purchase/search_product", {
                query: query,
                partner_id: this.state.partnerId,
                limit: 10,
            });
            console.log("[QP-DEBUG] search_product result:", result);

            const products = result.products || [];
            this.state.lastSearched = query;

            if (autoAdd && result.exact_match && products.length === 1) {
                this.addProduct(products[0]);
                return;
            }

            this.state.suggestions = products;
            this.state.activeSuggestion = products.length > 0 ? 0 : -1;
            this.state.showNoResult = (products.length === 0);
        } catch (e) {
            console.error("[QP-DEBUG] runSearch error:", e);
            if (e && e.stack) console.error("[QP-DEBUG] Stack:", e.stack);
            this.notification.add(
                _t("Search failed: ") + (e && e.message ? e.message : String(e)),
                { type: "danger" }
            );
        }
    }


    // ------------------------------------------------------------------
    // Line management (with UoM support)
    // ------------------------------------------------------------------

    addProduct(product) {
        console.log("[QP-DEBUG] addProduct called with:", product);

        if (!product || !product.id) {
            console.error("[QP-DEBUG] Invalid product passed to addProduct:", product);
            this.notification.add(
                _t("Cannot add product: invalid data received from server."),
                { type: "danger" }
            );
            return;
        }

        // Defensive: ensure all expected fields exist with safe defaults
        const safeProduct = {
            id: product.id,
            name: product.name || product.display_name || "(unnamed)",
            default_code: product.default_code || "",
            barcode: product.barcode || "",
            uom_id: parseInt(product.uom_id, 10) || null,
            uom_category_id: product.uom_category_id || null,
            uom_options: Array.isArray(product.uom_options) ? product.uom_options : [],
            packaging_options: Array.isArray(product.packaging_options) ? product.packaging_options : [],
            price: parseFloat(product.price) || 0,
            qty_from_packaging: parseFloat(product.qty_from_packaging) || 1,
            packaging_id: parseInt(product.packaging_id, 10) || null,
        };

        // If product already in lines, increment qty and move to top
        const existingIdx = this.state.lines.findIndex(l => l.product_id === safeProduct.id);
        if (existingIdx >= 0) {
            const existing = this.state.lines[existingIdx];
            existing.qty = (parseFloat(existing.qty) || 0) + safeProduct.qty_from_packaging;
            // Also increment packaging_qty if the new scan uses a packaging
            if (safeProduct.packaging_id) {
                existing.packaging_id = safeProduct.packaging_id;
                existing.packaging_qty = (parseFloat(existing.packaging_qty) || 0) + 1;
            }
            // Move to top of list
            if (existingIdx > 0) {
                this.state.lines.splice(existingIdx, 1);
                this.state.lines.unshift(existing);
            }
        } else {
            // New product: add to top of list
            // Calculate packaging qty based on current total qty. 
            // Default to 1 if it came directly from packaging scan.
            let pkgQty = 0;
            if (safeProduct.packaging_id && safeProduct.qty_from_packaging > 0) {
                pkgQty = safeProduct.qty_from_packaging / safeProduct.qty_from_packaging;
            }

            this.state.lines.unshift({
                product_id: safeProduct.id,
                name: safeProduct.name,
                default_code: safeProduct.default_code,
                barcode: safeProduct.barcode,
                qty: safeProduct.qty_from_packaging,
                packaging_id: safeProduct.packaging_id,
                packaging_qty: pkgQty,
                packaging_options: safeProduct.packaging_options,
                uom_id: safeProduct.uom_id,
                uom_category_id: safeProduct.uom_category_id,
                uom_options: safeProduct.uom_options,
                price_unit: safeProduct.price,
                discount_amount: 0,
            });
        }
        this.state.scanQuery = "";
        this.state.suggestions = [];
        this.state.showNoResult = false;
        this.state.activeSuggestion = -1;
        this.focusScanInput();
        this._debounceSaveSession();
    }

    updateLine(productId, field, value) {
        const line = this.state.lines.find(l => l.product_id === productId);
        if (!line) return;
        if (field === "uom_id" || field === "packaging_id") {
            line[field] = parseInt(value, 10) || null;

            // If packaging changes, recalculate total qty
            if (field === "packaging_id" && line.packaging_id && line.packaging_options) {
                const pkg = line.packaging_options.find(p => p.id === line.packaging_id);
                if (pkg) {
                    const currentPkgQty = parseFloat(line.packaging_qty) || 1;
                    line.qty = currentPkgQty * pkg.qty;
                }
            } else if (field === "packaging_id" && !line.packaging_id) {
                line.packaging_qty = 0;
            }
        } else if (field === "packaging_qty") {
            const num = parseFloat(value);
            line[field] = isNaN(num) ? 0 : num;

            // If packaging qty changes, update total qty based on packaging multiple
            if (line.packaging_id && line.packaging_options) {
                const pkg = line.packaging_options.find(p => p.id === line.packaging_id);
                if (pkg) {
                    line.qty = line[field] * pkg.qty;
                }
            }
        } else {
            const num = parseFloat(value);
            line[field] = isNaN(num) ? 0 : num;
        }
        this._debounceSaveSession();
    }

    removeLine(productId) {
        this.state.lines = this.state.lines.filter(l => l.product_id !== productId);
        this._debounceSaveSession();
    }

    stepQty(productId, delta) {
        const line = this.state.lines.find(l => l.product_id === productId);
        if (!line) return;
        const cur = parseFloat(line.qty) || 0;
        const next = cur + delta;
        // Minimum qty is 1 (consistent with duplicate scan modal behavior)
        line.qty = Math.max(1, next);
        this._debounceSaveSession();
    }

    // ------------------------------------------------------------------
    // UoM shortcut — open standard UoM list page
    // ------------------------------------------------------------------

    async openUomPage(productId) {
        try {
            const actionDict = await rpc("/andykanoz_quick_purchase/get_uom_action", {});
            actionDict.target = "new";
            this.action.doAction(actionDict, {
                onClose: async () => {
                    await this.refreshUomsForLine(productId);
                }
            });
        } catch (e) {
            // Fallback: open via client action
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Units of Measure",
                res_model: "uom.uom",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "new",
            }, {
                onClose: async () => {
                    await this.refreshUomsForLine(productId);
                }
            });
        }
    }

    async openCreateCategoryPopup() {
        try {
            const actionDict = await rpc("/andykanoz_quick_purchase/get_category_action", {});
            actionDict.target = actionDict.target || "new";
            this.action.doAction(actionDict);
        } catch (e) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Product Categories",
                res_model: "product.category",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "new",
            });
        }
    }

    async openCreatePublicCategoryPopup() {
        try {
            const actionDict = await rpc("/andykanoz_quick_purchase/get_public_category_action", {});
            actionDict.target = actionDict.target || "new";
            this.action.doAction(actionDict);
        } catch (e) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "Public Categories",
                res_model: "product.public.category",
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "new",
            });
        }
    }

    async refreshUomsForLine(productId) {
        const line = this.state.lines.find(l => l.product_id === productId);
        if (!line) return;
        try {
            const result = await rpc("/andykanoz_quick_purchase/refresh_uoms", {
                product_id: productId,
            });
            line.uom_options = result.uom_options || [];
            this.notification.add(
                _t("UoM options refreshed."),
                { type: "success" }
            );
        } catch (e) {
            this.notification.add(
                _t("Could not refresh UoM options: ") + (e.message || e),
                { type: "danger" }
            );
        }
    }


    // ------------------------------------------------------------------
    // Computed totals
    // ------------------------------------------------------------------

    lineSubtotal(line) {
        const qty = parseFloat(line.qty) || 0;
        const price = parseFloat(line.price_unit) || 0;
        const disc = parseFloat(line.discount_amount) || 0;
        return Math.max(0, (price - disc)) * qty;
    }

    totalQty() {
        return this.state.lines.reduce(
            (sum, l) => sum + (parseFloat(l.qty) || 0), 0
        );
    }

    totalDiscount() {
        return this.state.lines.reduce((sum, l) => {
            const qty = parseFloat(l.qty) || 0;
            const disc = parseFloat(l.discount_amount) || 0;
            return sum + (qty * disc);
        }, 0);
    }

    grandTotal() {
        return this.state.lines.reduce(
            (sum, l) => sum + this.lineSubtotal(l), 0
        );
    }

    formatMoney(value, withSymbol = false) {
        const num = parseFloat(value) || 0;
        let formatted;
        try {
            formatted = num.toLocaleString("id-ID", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2,
            });
        } catch (_e) {
            formatted = num.toFixed(0);
        }
        return withSymbol ? "Rp " + formatted : formatted;
    }

    // ------------------------------------------------------------------
    // Editable money input handlers (Unit Price & Disc/Unit)
    // ------------------------------------------------------------------

    _parseMoneyInput(raw) {
        if (raw === null || raw === undefined) return 0;
        let s = String(raw).trim();
        if (!s) return 0;
        s = s.replace(/[^\d.,\-]/g, "");
        if (!s) return 0;
        const lastComma = s.lastIndexOf(",");
        const lastDot = s.lastIndexOf(".");
        if (lastComma > lastDot) {
            s = s.replace(/\./g, "").replace(",", ".");
        } else if (lastDot > lastComma) {
            s = s.replace(/,/g, "");
        } else {
            s = s.replace(/,/g, "");
        }
        const num = parseFloat(s);
        return isNaN(num) ? 0 : num;
    }

    onPriceFocus(ev, line, field) {
        const cur = parseFloat(line[field]) || 0;
        ev.target.value = cur === 0 ? "" : String(cur);
        setTimeout(() => { try { ev.target.select(); } catch (_e) {} }, 0);
    }

    onPriceBlur(ev, line, field) {
        const num = this._parseMoneyInput(ev.target.value);
        line[field] = num;
        ev.target.value = this.formatMoney(num);
        this._debounceSaveSession();
    }

    onPriceKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            ev.target.blur();
        }
    }




    // ------------------------------------------------------------------
    // Quick-create product modal
    // ------------------------------------------------------------------

    openCreateModal() {
        const q = (this.state.lastSearched || "").trim();
        const looksLikeCode = /^[\d\-]+$/.test(q) && q.length >= 4;
        this.state.newProduct = {
            name: looksLikeCode ? "" : q,
            barcode: looksLikeCode ? q : "",
            default_code: "",
            cost: 0,
            categ_id: null,
            categ_name: "",
            public_categ_ids: [],
            is_storable: false,
            available_in_pos: false,
            is_published: false,
        };
        // Reset autocomplete states
        this.state.categQuery = "";
        this.state.categSuggestions = [];
        this.state.categActiveSuggestion = -1;
        this.state.showCategDropdown = false;
        this.state.publicCategQuery = "";
        this.state.publicCategSuggestions = [];
        this.state.publicCategActiveSuggestion = -1;
        this.state.showPublicCategDropdown = false;

        this.state.showCreateModal = true;
        setTimeout(() => {
            if (this.newProductNameRef.el) {
                this.newProductNameRef.el.focus();
            }
        }, 50);
    }

    closeCreateModal() {
        this.state.showCreateModal = false;
        this.state.creatingProduct = false;
        this.state.showCategDropdown = false;
        this.state.showPublicCategDropdown = false;
        this.focusScanInput();
    }

    onModalBackdropClick() {
        this.closeCreateModal();
    }

    // ------------------------------------------------------------------
    // Category autocomplete (single-select, local filter)
    // ------------------------------------------------------------------

    onCategInput(ev) {
        const query = ev.target.value;
        this.state.categQuery = query;
        this._filterCategSuggestions(query);
        this.state.showCategDropdown = true;
        // Clear selection if user edits text
        this.state.newProduct.categ_id = null;
        this.state.newProduct.categ_name = "";
    }

    onCategFocus() {
        this._filterCategSuggestions(this.state.categQuery);
        this.state.showCategDropdown = true;
    }

    onCategBlur() {
        setTimeout(() => { this.state.showCategDropdown = false; }, 200);
    }

    onCategKeydown(ev) {
        const list = this.state.categSuggestions;
        if (ev.key === "ArrowDown" && list.length > 0) {
            ev.preventDefault();
            this.state.categActiveSuggestion = Math.min(
                this.state.categActiveSuggestion + 1, list.length - 1
            );
            return;
        }
        if (ev.key === "ArrowUp" && list.length > 0) {
            ev.preventDefault();
            this.state.categActiveSuggestion = Math.max(
                this.state.categActiveSuggestion - 1, 0
            );
            return;
        }
        if (ev.key === "Enter" && this.state.categActiveSuggestion >= 0) {
            ev.preventDefault();
            this.selectCateg(list[this.state.categActiveSuggestion]);
            return;
        }
        if (ev.key === "Escape") {
            this.state.showCategDropdown = false;
        }
    }

    _filterCategSuggestions(query) {
        const all = this.state.metadata.categories || [];
        if (!query || !query.trim()) {
            this.state.categSuggestions = all.slice(0, 30);
        } else {
            const q = query.toLowerCase();
            this.state.categSuggestions = all
                .filter(c => c.name.toLowerCase().includes(q))
                .slice(0, 30);
        }
        this.state.categActiveSuggestion =
            this.state.categSuggestions.length > 0 ? 0 : -1;
    }

    selectCateg(categ) {
        if (!categ) return;
        this.state.newProduct.categ_id = categ.id;
        this.state.newProduct.categ_name = categ.name;
        this.state.categQuery = categ.name;
        this.state.showCategDropdown = false;
        this.state.categSuggestions = [];
    }

    // ------------------------------------------------------------------
    // Public / eCommerce category autocomplete (multi-select with tags)
    // ------------------------------------------------------------------

    onPublicCategInput(ev) {
        const query = ev.target.value;
        this.state.publicCategQuery = query;
        this._filterPublicCategSuggestions(query);
        this.state.showPublicCategDropdown = true;
    }

    onPublicCategFocus() {
        this._filterPublicCategSuggestions(this.state.publicCategQuery);
        this.state.showPublicCategDropdown = true;
    }

    onPublicCategBlur() {
        setTimeout(() => { this.state.showPublicCategDropdown = false; }, 200);
    }

    onPublicCategKeydown(ev) {
        const list = this.state.publicCategSuggestions;
        if (ev.key === "ArrowDown" && list.length > 0) {
            ev.preventDefault();
            this.state.publicCategActiveSuggestion = Math.min(
                this.state.publicCategActiveSuggestion + 1, list.length - 1
            );
            return;
        }
        if (ev.key === "ArrowUp" && list.length > 0) {
            ev.preventDefault();
            this.state.publicCategActiveSuggestion = Math.max(
                this.state.publicCategActiveSuggestion - 1, 0
            );
            return;
        }
        if (ev.key === "Enter" && this.state.publicCategActiveSuggestion >= 0) {
            ev.preventDefault();
            this.selectPublicCateg(list[this.state.publicCategActiveSuggestion]);
            return;
        }
        if (ev.key === "Escape") {
            this.state.showPublicCategDropdown = false;
        }
    }

    _filterPublicCategSuggestions(query) {
        const all = this.state.metadata.public_categories || [];
        const selectedIds = this.state.newProduct.public_categ_ids;
        // Exclude already selected
        let available = all.filter(c => !selectedIds.includes(c.id));
        if (query && query.trim()) {
            const q = query.toLowerCase();
            available = available.filter(c => c.name.toLowerCase().includes(q));
        }
        this.state.publicCategSuggestions = available.slice(0, 20);
        this.state.publicCategActiveSuggestion =
            this.state.publicCategSuggestions.length > 0 ? 0 : -1;
    }

    selectPublicCateg(categ) {
        if (!categ) return;
        if (!this.state.newProduct.public_categ_ids.includes(categ.id)) {
            this.state.newProduct.public_categ_ids.push(categ.id);
        }
        this.state.publicCategQuery = "";
        this._filterPublicCategSuggestions("");
        this.state.showPublicCategDropdown = false;
    }

    removePublicCateg(categId) {
        const ids = this.state.newProduct.public_categ_ids;
        const idx = ids.indexOf(categId);
        if (idx >= 0) ids.splice(idx, 1);
    }

    getPublicCategName(categId) {
        const cat = (this.state.metadata.public_categories || []).find(c => c.id === categId);
        return cat ? cat.name : "";
    }

    isCreateNewProductDisabled() {
        const np = this.state.newProduct;
        if (!np.name || !np.name.trim()) {
            return true;
        }
        if (!np.categ_id) {
            return true;
        }
        if (this.state.categQuery && this.state.categQuery.trim() && this.state.categQuery !== np.categ_name) {
            return true;
        }
        if (this.state.publicCategQuery && this.state.publicCategQuery.trim()) {
            return true;
        }
        return false;
    }

    // Track Inventory checkbox handler
    onTrackInventoryToggle(ev) {
        const oldValue = this.state.newProduct.is_storable;
        const newValue = ev.target.checked;
        this.state.newProduct.is_storable = newValue;
        console.log("[QP] 'Track Inventory' checkbox changed:");
        console.log("  Old:", oldValue, "→ New:", newValue);
        console.log("  is_storable will be:", newValue);
    }

    // ------------------------------------------------------------------

    async onSubmitNewProduct() {
        const np = this.state.newProduct;
        if (!np.name || !np.name.trim()) {
            this.notification.add(_t("Product name is required."), { type: "warning" });
            return;
        }
        if (!np.categ_id) {
            this.notification.add(_t("Product category is required."), { type: "warning" });
            return;
        }
        if (this.state.categQuery && this.state.categQuery.trim() && this.state.categQuery !== np.categ_name) {
            this.notification.add(_t("Please select a valid product category."), { type: "warning" });
            return;
        }
        if (this.state.publicCategQuery && this.state.publicCategQuery.trim()) {
            this.notification.add(_t("Please select or clear the public category input."), { type: "warning" });
            return;
        }
        this.state.creatingProduct = true;
        try {
            const product = await rpc("/andykanoz_quick_purchase/create_product", {
                name: np.name,
                barcode: np.barcode || null,
                default_code: np.default_code || null,
                cost: parseFloat(np.cost) || 0,
                categ_id: np.categ_id || null,
                partner_id: this.state.partnerId,
                is_storable: np.is_storable !== false,
                available_in_pos: !!np.available_in_pos,
                is_published: !!np.is_published,
                public_categ_ids: np.public_categ_ids || [],
            });
            console.log("[QP] Product created successfully");
            console.log("  is_storable sent:", np.is_storable);
            console.log("  Response:", product);
            this.notification.add(
                _t("Product created: ") + product.name,
                { type: "success" }
            );
            this.closeCreateModal();
            this.addProduct(product);
        } catch (e) {
            console.error("[QP] Failed to create product", e);
            const serverMessage = e && e.data && (e.data.message || e.data.error) ?
                (e.data.message || e.data.error) : null;
            const message = serverMessage || e.message || String(e);
            this.notification.add(
                _t("Failed to create product: ") + message,
                { type: "danger" }
            );
        } finally {
            this.state.creatingProduct = false;
        }
    }


    // ------------------------------------------------------------------
    // Camera barcode scanner (Once + Continuous modes)
    // ------------------------------------------------------------------

    openCameraOnce() {
        this.state.cameraMode = "once";
        this._startCamera();
    }

    openCameraContinuous() {
        this.state.cameraMode = "continuous";
        this._startCamera();
    }

    async _startCamera() {
        // Blur any focused input to prevent keyboard from appearing
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }

        this.state.cameraError = null;
        this.state.lastDetected = null;
        this.state.torchSupported = false;
        this.state.torchOn = false;
        this.state.scannedCount = 0;
        this.state.lastScanStatus = null;
        this.state.lastScanMessage = null;
        this.state.showCameraModal = true;
        this._lastScannedCode = null;
        this._lastScannedAt = 0;

        // Initialize Web Audio API (must happen on user gesture)
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext && !this._audioCtx) {
            this._audioCtx = new AudioContext();
        }
        if (this._audioCtx && this._audioCtx.state === "suspended") {
            this._audioCtx.resume();
        }

        if (typeof window.BarcodeDetector === "undefined") {
            this.state.cameraError = _t(
                "Your browser does not support the Barcode Detector API. " +
                "Please use Chrome on Android, or use the manual input above."
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
                    facingMode: { ideal: "environment" },
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

        setTimeout(() => {
            if (!this.cameraVideoRef.el) {
                this.state.cameraError = _t("Video element not ready.");
                this.stopCamera();
                return;
            }
            this.cameraVideoRef.el.srcObject = this._cameraStream;
            this._cameraTrack = this._cameraStream.getVideoTracks()[0];

            // Torch detection with polling fallback (some Android devices need time)
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
                if (checkAttempts < 15 && this.state.showCameraModal) {
                    setTimeout(checkTorch, 400);
                }
            };
            checkTorch();

            this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
        }, 100);
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

                // Anti-duplicate guard: ignore same barcode within 2 seconds
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
            // transient errors are ignored
        }
    }

    async _onBarcodeDetected(barcode) {
        // Pause scan loop during processing
        const wasLoopActive = this._scanLoopHandle !== null;
        if (wasLoopActive) {
            clearInterval(this._scanLoopHandle);
            this._scanLoopHandle = null;
        }

        try {
            // Search and add the product
            const result = await this._scanAndAddProduct(barcode);

            // Play appropriate sound
            this._playScanSound(result);

            // "Once" mode: close camera after first scan
            if (this.state.cameraMode === "once") {
                this.stopCamera();
                this.state.showCameraModal = false;
                // Duplicate confirmation modal will be shown by _scanAndAddProduct
                // — skip the legacy notification path, the modal is the new UX.
                if (result === "duplicate_pending") {
                    return;
                }
                // Show notification for "once" mode when product already exists
                if (result === "incremented") {
                    const line = this.state.lines.find(l => l.barcode === barcode || l.default_code === barcode);
                    const name = line ? line.name : barcode;
                    const qty = line ? line.qty : "?";
                    this.notification.add(
                        _t("⚠ Product already in list: ") + name + _t(" — Qty updated to ") + qty + _t(", moved to top"),
                        { type: "warning", sticky: false }
                    );
                }
                return;
            }

            // "Continuous" mode: show flash feedback and keep camera open
            if (result === "added") {
                this.state.lastScanStatus = "success";
                const line = this.state.lines.find(l => l.barcode === barcode || l.default_code === barcode);
                this.state.lastScanMessage = _t("Added: ") + (line ? line.name : barcode);
                this.state.scannedCount = this.state.scannedCount + 1;
            } else if (result === "incremented") {
                this.state.lastScanStatus = "duplicate";
                const line = this.state.lines.find(l => l.barcode === barcode || l.default_code === barcode);
                const qtyInfo = line ? (" (Qty: " + line.qty + ")") : "";
                this.state.lastScanMessage = _t("⚠ Already in list! ") + (line ? line.name : barcode) + qtyInfo + _t(" — moved to top");
                this.state.scannedCount = this.state.scannedCount + 1;
            } else if (result === "notfound") {
                this.state.lastScanStatus = "notfound";
                this.state.lastScanMessage = _t("Not found: ") + barcode;
            } else {
                this.state.lastScanStatus = "notfound";
                this.state.lastScanMessage = _t("Error: ") + barcode;
            }

            // Clear flash feedback (longer for duplicate info)
            const flashDuration = result === "incremented" ? 2500 : 1500;
            setTimeout(() => {
                this.state.lastScanStatus = null;
                this.state.lastScanMessage = null;
            }, flashDuration);
        } finally {
            // Restart scan loop in continuous mode
            if (this.state.cameraMode === "continuous" && this.state.showCameraModal) {
                this._scanLoopHandle = setInterval(() => this._scanFrame(), 350);
            }
        }
    }

    /**
     * Search product by barcode and add to lines.
     * Returns: "added" | "incremented" | "notfound" | "error"
     */
    async _scanAndAddProduct(barcode) {
        try {
            const result = await rpc("/andykanoz_quick_purchase/search_product", {
                query: barcode,
                partner_id: this.state.partnerId,
                limit: 10,
            });

            const products = result.products || [];
            // Store searched barcode so Quick Create can auto-fill it
            this.state.lastSearched = barcode;

            if (!result.exact_match || products.length === 0) {
                // In "once" mode, put the barcode in scan field for manual handling
                if (this.state.cameraMode === "once") {
                    this.state.scanQuery = barcode;
                    this.state.suggestions = products;
                    this.state.showNoResult = (products.length === 0);
                }
                if (products.length === 0) {
                    return "notfound";
                }
            }

            // Use exact match (first product)
            const product = products[0];
            const existing = this.state.lines.find(l => l.product_id === product.id);

            // ONCE mode + already in list → defer adding, open confirmation modal
            if (existing && this.state.cameraMode === "once") {
                this.state.duplicateProduct = product;
                this.state.duplicateExistingLine = existing;
                this.state.duplicateAddQty = 1;
                this.state.showDuplicateModal = true;
                return "duplicate_pending";
            }

            this.addProduct(product);
            return existing ? "incremented" : "added";
        } catch (e) {
            console.error("[QP] _scanAndAddProduct error:", e);
            return "error";
        }
    }

    // ------------------------------------------------------------------
    // Duplicate scan confirmation modal (Once mode)
    // ------------------------------------------------------------------

    incrementDuplicateQty() {
        const cur = parseInt(this.state.duplicateAddQty, 10) || 1;
        this.state.duplicateAddQty = Math.min(cur + 1, 9999);
    }

    decrementDuplicateQty() {
        const cur = parseInt(this.state.duplicateAddQty, 10) || 1;
        this.state.duplicateAddQty = Math.max(cur - 1, 1);
    }

    onDuplicateQtyInput(ev) {
        const raw = parseInt(ev.target.value, 10);
        if (isNaN(raw) || raw < 1) {
            this.state.duplicateAddQty = 1;
        } else if (raw > 9999) {
            this.state.duplicateAddQty = 9999;
        } else {
            this.state.duplicateAddQty = raw;
        }
    }

    confirmDuplicateAdd() {
        const product = this.state.duplicateProduct;
        const existingLine = this.state.duplicateExistingLine;
        const addQty = parseInt(this.state.duplicateAddQty, 10) || 1;

        if (!product || !existingLine) {
            this._closeDuplicateModal();
            return;
        }

        // Find current index of the existing line (state may have changed)
        const idx = this.state.lines.findIndex(l => l.product_id === existingLine.product_id);
        if (idx < 0) {
            // Line was removed in the meantime — fall back to addProduct flow
            this._closeDuplicateModal();
            this.addProduct(product);
            return;
        }

        const line = this.state.lines[idx];
        line.qty = (parseFloat(line.qty) || 0) + addQty;

        // Move to top of list
        if (idx > 0) {
            this.state.lines.splice(idx, 1);
            this.state.lines.unshift(line);
        }

        this._playScanSound("success");
        this._closeDuplicateModal();
        this.focusScanInput();
        this._debounceSaveSession();
    }

    cancelDuplicateAdd() {
        this._closeDuplicateModal();
        this.focusScanInput();
    }

    _closeDuplicateModal() {
        this.state.showDuplicateModal = false;
        this.state.duplicateProduct = null;
        this.state.duplicateExistingLine = null;
        this.state.duplicateAddQty = 1;
    }

    // ------------------------------------------------------------------
    // Scan sound feedback (Web Audio API oscillator)
    // ------------------------------------------------------------------

    _playScanSound(type = "success") {
        if (!this._audioCtx) return;
        try {
            const osc = this._audioCtx.createOscillator();
            const gain = this._audioCtx.createGain();
            osc.connect(gain);
            gain.connect(this._audioCtx.destination);

            if (type === "added" || type === "incremented" || type === "success") {
                // Pleasant high-pitched beep for success
                osc.type = "sine";
                osc.frequency.setValueAtTime(880, this._audioCtx.currentTime);
                gain.gain.setValueAtTime(0.6, this._audioCtx.currentTime);
                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.1);
            } else if (type === "notfound" || type === "error") {
                // Harsh low buzzer for error/not found
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(250, this._audioCtx.currentTime);
                gain.gain.setValueAtTime(0.8, this._audioCtx.currentTime);
                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.35);
            } else if (type === "duplicate") {
                // Middle-pitched beep for duplicate
                osc.type = "sine";
                osc.frequency.setValueAtTime(660, this._audioCtx.currentTime);
                gain.gain.setValueAtTime(0.6, this._audioCtx.currentTime);
                osc.start(this._audioCtx.currentTime);
                osc.stop(this._audioCtx.currentTime + 0.15);
            }
        } catch (_e) {
            // Audio errors are non-critical, ignore silently
        }
    }

    // ------------------------------------------------------------------
    // Camera controls
    // ------------------------------------------------------------------

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

    closeCameraScanner() {
        this.stopCamera();
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


    // ------------------------------------------------------------------
    // Create the actual purchase order
    // ------------------------------------------------------------------

    async onCreatePO(redirect = true) {
        if (!this.state.partnerId) {
            this.notification.add(_t("Please select a vendor."), { type: "warning" });
            return;
        }
        if (this.state.lines.length === 0) {
            this.notification.add(_t("No lines to send."), { type: "warning" });
            return;
        }
        const badLines = this.state.lines.filter(l => (parseFloat(l.qty) || 0) <= 0);
        if (badLines.length > 0) {
            this.notification.add(
                _t("Some lines have zero quantity. Fix them or remove them first."),
                { type: "warning" }
            );
            return;
        }

        this.state.creating = true;
        try {
            const payload = {
                partner_id: this.state.partnerId,
                lines: this.state.lines.map(l => ({
                    product_id: l.product_id,
                    qty: parseFloat(l.qty) || 0,
                    price_unit: parseFloat(l.price_unit) || 0,
                    discount_amount: parseFloat(l.discount_amount) || 0,
                    uom_id: l.uom_id || null,
                    packaging_id: l.packaging_id || null,
                    qty_from_packaging: l.qty_from_packaging || 1,
                })),
            };
            const result = await rpc(
                "/andykanoz_quick_purchase/create_po",
                payload
            );
            this.notification.add(
                _t("Purchase Order created: ") + result.name,
                { type: "success" }
            );

            if (redirect) {
                // Remove the session LOCALLY from the UI so it's not rendered while redirecting
                if (this.state.activeSessionId) {
                    const currentSessionId = this.state.activeSessionId;
                    const idx = this.state.sessions.findIndex(s => s.id === currentSessionId);
                    if (idx >= 0) {
                        this.state.sessions.splice(idx, 1);
                    }
                    this.state.activeSessionId = null;

                    rpc("/andykanoz_quick_purchase/clear_session", { session_id: currentSessionId }).catch(e => console.warn(e));
                }

                // Allow UI to render the "empty" state for a split second to detach heavy DOM
                // and then trigger the heavy action to prevent frozen/blank screen.
                setTimeout(() => {
                    this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "purchase.order",
                        res_id: result.id,
                        views: [[false, "form"]],
                        target: "current",
                    }, { clearBreadcrumbs: true });
                }, 50);

                return;
            } else {
                // Stay on the same screen to create another PO for the same vendor
                setTimeout(() => this.focusScanInput(), 100);

                // Remove the current session since it was converted to a PO
                if (this.state.activeSessionId) {
                    const currentSessionId = this.state.activeSessionId;
                    const idx = this.state.sessions.findIndex(s => s.id === currentSessionId);
                    if (idx >= 0) {
                        this.state.sessions.splice(idx, 1);
                    }
                    rpc("/andykanoz_quick_purchase/clear_session", { session_id: currentSessionId }).catch(e => console.warn(e));

                    if (this.state.sessions.length > 0) {
                        this._restoreSession(this.state.sessions[0].id);
                    } else {
                        // User requested to keep 0 sessions, so just clear the view
                        this.state.activeSessionId = null;
                        this.state.partnerId = null;
                        this.state.partnerName = "";
                        this.state.vendorQuery = "";
                        this.state.lines = [];
                        localStorage.removeItem(QP_ACTIVE_SESSION_KEY);
                    }
                } else {
                    this.state.lines = [];
                    this.state.scanQuery = "";
                }
            }

            this.state.sessionStatus = null;
        } catch (e) {
            this.notification.add(
                _t("Failed to create Purchase Order: ") + (e.message || e),
                { type: "danger" }
            );
        } finally {
            if (!redirect) {
                this.state.creating = false;
            }
        }
    }
}

registry
    .category("actions")
    .add("andykanoz_quick_purchase.QuickPurchase", QuickPurchase);




