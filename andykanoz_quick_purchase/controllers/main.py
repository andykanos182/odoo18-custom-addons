# -*- coding: utf-8 -*-
import logging
import traceback
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class QuickPurchaseController(http.Controller):
    """JSON-RPC endpoints for the Quick Purchase Entry OWL UI."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_purchase_access(self):
        if not request.env.user.has_group("purchase.group_purchase_user"):
            raise AccessError(_("You need Purchase User access to use Quick Purchase Entry."))

    def _get_uoms_for_category(self, category_id):
        """Return list of UoMs in the given UoM category, ordered by factor."""
        if not category_id:
            return []
        uoms = request.env["uom.uom"].search(
            [("category_id", "=", category_id)],
            order="factor desc, name asc",
        )
        return [
            {
                "id": u.id,
                "name": u.name,
                "factor": u.factor,
                "uom_type": u.uom_type,
            }
            for u in uoms
        ]

    def _serialize_product(self, product, partner_id=None):
        """Serialize product for the frontend, with safe fallbacks."""
        try:
            price = product.get_last_purchase_price(partner_id=partner_id)
        except Exception as e:
            _logger.warning("Failed to get last price for product %s: %s", product.id, e)
            price = product.standard_price or 0.0
        
        # Safe UoM extraction — some products may have unusual UoM setup
        uom_id = False
        uom_name = ""
        category_id = None
        uom_options = []
        
        try:
            # For purchase orders, we should default to the Purchase UoM (uom_po_id)
            target_uom = product.uom_po_id if hasattr(product, 'uom_po_id') and product.uom_po_id else product.uom_id
            if target_uom:
                uom_id = target_uom.id
                uom_name = target_uom.name or ""
                if target_uom.category_id:
                    category_id = target_uom.category_id.id
                    uom_options = self._get_uoms_for_category(category_id)
        except Exception as e:
            _logger.warning("Failed to extract UoM for product %s: %s", product.id, e)
        
        # Check if packaging info was passed down via context (set during packaging search)
        qty_from_packaging = product.env.context.get('qty_from_packaging', 1)
        packaging_id = product.env.context.get('packaging_id', False)

        packaging_options = []
        if hasattr(product, "packaging_ids") and product.packaging_ids:
            for pkg in product.packaging_ids:
                packaging_options.append({
                    "id": pkg.id,
                    "name": pkg.name,
                    "qty": pkg.qty,
                })

        return {
            "id": product.id,
            "name": product.display_name or product.name or "(unnamed)",
            "default_code": product.default_code or "",
            "barcode": product.barcode or "",
            "uom_id": uom_id,
            "uom_name": uom_name,
            "uom_category_id": category_id,
            "uom_options": uom_options or [],
            "packaging_options": packaging_options,
            "price": float(price or 0.0),
            "image_url": "/web/image/product.product/%d/image_128" % product.id,
            "qty_from_packaging": qty_from_packaging,
            "packaging_id": packaging_id,
        }

    # ------------------------------------------------------------------
    # 1. Vendors dropdown (kept for backwards compat; not used by Many2X)
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/get_vendors",
        type="json",
        auth="user",
    )
    def get_vendors(self, query=None, limit=20):
        """Search vendors using the same logic as the standard PO Vendor field.

        Uses res.partner.name_search() with the supplier search mode context,
        which is exactly what Odoo's PO form uses. This ensures the vendor
        list shown in Quick Entry matches what users see in PO/RFQ Vendor
        selectors — including vendors that have supplier_rank=0 but are
        properly configured as suppliers.
        """
        self._check_purchase_access()
        Partner = request.env["res.partner"].with_context(
            res_partner_search_mode="supplier",
            show_vat=True,
        )
        # name_search returns list of (id, display_name) tuples
        name_search_results = Partner.name_search(
            name=query or "",
            args=None,
            operator="ilike",
            limit=limit,
        )
        if not name_search_results:
            return []
        partner_ids = [r[0] for r in name_search_results]
        # Read additional fields for the dropdown display
        partners = Partner.browse(partner_ids).read(
            ["id", "name", "ref", "vat"]
        )
        # Preserve the order from name_search (Odoo orders by relevance)
        partner_map = {p["id"]: p for p in partners}
        result = []
        for pid in partner_ids:
            p = partner_map.get(pid)
            if not p:
                continue
            result.append({
                "id": p["id"],
                "name": p["name"] or "",
                "ref": p["ref"] or "",
                "vat": p["vat"] or "",
            })
        return result

    # ------------------------------------------------------------------
    # 2. Product search (barcode, sku, name)
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/search_product",
        type="json",
        auth="user",
    )
    def search_product(self, query, partner_id=None, limit=10):
        self._check_purchase_access()
        if not query or not query.strip():
            return {"products": [], "exact_match": False}

        query = query.strip()
        Product = request.env["product.product"]
        Packaging = request.env["product.packaging"]
        base_domain = [("purchase_ok", "=", True)]

        # 1. Exact packaging barcode match
        packaging_match = Packaging.search([("barcode", "=", query)], limit=1)
        if packaging_match:
            # Packaging could be linked to product.product or product.template
            prod = packaging_match.product_id
            if not prod and hasattr(packaging_match, 'product_tmpl_id') and packaging_match.product_tmpl_id:
                # Find the first variant
                prod = packaging_match.product_tmpl_id.product_variant_id
            
            if prod and prod.purchase_ok:
                # Pass packaging qty in context so _serialize_product can attach it
                product_env = Product.with_context(qty_from_packaging=packaging_match.qty, packaging_id=packaging_match.id)
                return {
                    "products": [self._serialize_product(product_env.browse(prod.id), partner_id)],
                    "exact_match": True,
                }

        # 2. Exact product barcode match
        barcode_match = Product.search(
            base_domain + [("barcode", "=", query)], limit=1
        )
        if barcode_match:
            return {
                "products": [self._serialize_product(barcode_match, partner_id)],
                "exact_match": True,
            }

        # 2. Exact internal reference match
        sku_match = Product.search(
            base_domain + [("default_code", "=", query)], limit=1
        )
        if sku_match:
            return {
                "products": [self._serialize_product(sku_match, partner_id)],
                "exact_match": True,
            }

        # 3. Fuzzy: name OR partial code OR partial barcode
        fuzzy = Product.search(
            base_domain
            + [
                "|", "|",
                ("name", "ilike", query),
                ("default_code", "ilike", query),
                ("barcode", "ilike", query),
            ],
            limit=limit,
        )
        return {
            "products": [
                self._serialize_product(p, partner_id) for p in fuzzy
            ],
            "exact_match": False,
        }

    # ------------------------------------------------------------------
    # 3. Get price for a single product
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/get_price",
        type="json",
        auth="user",
    )
    def get_price(self, product_id, partner_id=None):
        self._check_purchase_access()
        product = request.env["product.product"].browse(int(product_id))
        if not product.exists():
            return {"price": 0.0}
        return {"price": product.get_last_purchase_price(partner_id=partner_id)}

    # ------------------------------------------------------------------
    # 4. Quick-create product
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/create_product",
        type="json",
        auth="user",
    )
    def create_product(self, name, barcode=None, default_code=None,
                       cost=0.0, categ_id=None, uom_id=None,
                       partner_id=None, is_storable=True,
                       available_in_pos=False, is_published=False,
                       public_categ_ids=None):
        self._check_purchase_access()
        if not name or not name.strip():
            raise UserError(_("Product name is required."))

        ProductTemplate = request.env["product.template"]

        if not categ_id:
            raise UserError(_("Product category is required."))

        # Always create as consumable/goods for purchase orders
        vals = {
            "name": name.strip(),
            "type": "consu",  # Always consumable for purchase
            "purchase_ok": True,
            "sale_ok": True,
            "standard_price": float(cost or 0.0),
            "is_storable": bool(is_storable),  # Set is_storable based on checkbox
        }
        
        _logger.info("Quick create product - is_storable: %s", "True (Track Inventory)" if is_storable else "False (Don't Track)")
        if barcode:
            vals["barcode"] = barcode.strip()
        if default_code:
            vals["default_code"] = default_code.strip()
        if categ_id:
            vals["categ_id"] = int(categ_id)
        if uom_id:
            vals["uom_id"] = int(uom_id)
            vals["uom_po_id"] = int(uom_id)
        elif "uom_id" in ProductTemplate._fields:
            # Ensure the product template gets a valid unit of measure.
            # Quick Create does not currently ask for UoM, so use a known
            # reference UoM (Unit) or the first available UoM.
            default_uom = request.env.ref(
                "uom.product_uom_unit", raise_if_not_found=False
            )
            if not default_uom:
                default_uom = request.env["uom.uom"].search([], limit=1)
            if default_uom:
                vals["uom_id"] = int(default_uom.id)
                if "uom_po_id" in ProductTemplate._fields:
                    vals["uom_po_id"] = int(default_uom.id)
            else:
                _logger.warning(
                    "Quick create product: no valid UoM available, product template creation may fail."
                )

        # Is Published (only if website module is installed)
        if is_published and "is_published" in ProductTemplate._fields:
            vals["is_published"] = True

        # Public / eCommerce categories (only if website_sale is installed)
        if public_categ_ids and "public_categ_ids" in ProductTemplate._fields:
            ids = [int(x) for x in public_categ_ids if x]
            if ids:
                vals["public_categ_ids"] = [(6, 0, ids)]

        if "available_in_pos" in ProductTemplate._fields:
            vals["available_in_pos"] = bool(available_in_pos)

        _logger.debug("Quick create product request, partner_id=%s, vals=%s", partner_id, vals)
        try:
            template = ProductTemplate.create(vals)
            _logger.info("Product created - ID: %d, is_storable: %s", template.id, template.is_storable)
        except Exception as e:
            _logger.exception("Quick create product failed: %s", e)
            _logger.debug("Quick create product traceback:\n%s", traceback.format_exc())
            raise UserError(_("Could not create product: %s") % str(e))

        product = template.product_variant_id
        return self._serialize_product(product, partner_id)

    # ------------------------------------------------------------------
    # 5. Form metadata
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/form_metadata",
        type="json",
        auth="user",
    )
    def form_metadata(self):
        self._check_purchase_access()

        # Internal product categories — use browse to guarantee computed fields work
        categ_records = request.env["product.category"].search(
            [], order="complete_name asc"
        )
        categories = []
        for c in categ_records:
            try:
                categories.append({
                    "id": c.id,
                    "name": c.complete_name or c.name or "Category #%d" % c.id,
                })
            except Exception:
                categories.append({"id": c.id, "name": c.name or ""})

        # UoMs (still needed for line-level UoM selectors)
        uom_records = request.env["uom.uom"].search([], order="name asc")
        uoms = [{"id": u.id, "name": u.name} for u in uom_records]

        # Public / website categories (only if website_sale is installed)
        public_categs = []
        if "product.public.category" in request.env:
            pub_records = request.env["product.public.category"].search(
                [], order="name asc"
            )
            for p in pub_records:
                try:
                    public_categs.append({
                        "id": p.id,
                        "name": p.display_name or p.name or "",
                    })
                except Exception:
                    public_categs.append({"id": p.id, "name": p.name or ""})

        return {
            "categories": categories,
            "uoms": uoms,
            "public_categories": public_categs,
        }

    # ------------------------------------------------------------------
    # 6. Create purchase order from lines
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/create_po",
        type="json",
        auth="user",
    )
    def create_po(self, partner_id, lines):
        """Create a draft purchase.order.

        Each line may specify a `uom_id` different from the product's
        default UoM (as long as it's in the same category). Odoo's PO
        line handles UoM conversion automatically when saving.
        """
        self._check_purchase_access()
        if not partner_id:
            raise UserError(_("Please select a vendor."))
        if not lines:
            raise UserError(_("Cannot create an empty Purchase Order."))

        order_lines = []
        for ln in lines:
            product_id = int(ln.get("product_id") or 0)
            qty = float(ln.get("qty") or 0.0)
            price = float(ln.get("price_unit") or 0.0)
            disc_amount = float(ln.get("discount_amount") or 0.0)
            uom_id = int(ln.get("uom_id") or 0) or None
            packaging_id = int(ln.get("packaging_id") or 0) or None

            if not product_id or qty <= 0:
                continue

            # Convert nominal discount per unit -> percentage.
            discount_pct = 0.0
            if price > 0 and disc_amount > 0:
                discount_pct = (disc_amount / price) * 100.0
                if discount_pct > 100.0:
                    discount_pct = 100.0

            line_vals = {
                "product_id": product_id,
                "product_qty": qty,
                "price_unit": price,
            }
            if uom_id:
                line_vals["product_uom"] = uom_id
            if packaging_id:
                line_vals["product_packaging_id"] = packaging_id
                # Only map the packaging quantity if the line has a valid packaging
                qty_from_packaging = ln.get("qty_from_packaging", 1)
                # Usually product_packaging_qty is the number of boxes
                if qty_from_packaging > 0:
                    line_vals["product_packaging_qty"] = qty / qty_from_packaging

            if "discount" in request.env["purchase.order.line"]._fields:
                line_vals["discount"] = discount_pct
            order_lines.append((0, 0, line_vals))

        if not order_lines:
            raise UserError(_("No valid lines to create."))

        po_vals = {
            "partner_id": int(partner_id),
            "order_line": order_lines,
        }
        try:
            po = request.env["purchase.order"].create(po_vals)
            if hasattr(po, "_compute_tax_totals"):
                po._compute_tax_totals()
        except Exception as e:
            _logger.exception("Quick PO creation failed")
            raise UserError(_("Could not create Purchase Order: %s") % str(e))

        return {
            "id": po.id,
            "name": po.name,
        }

    # ------------------------------------------------------------------
    # 7. Get UoM management action (for the shortcut button)
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/get_uom_action",
        type="json",
        auth="user",
    )
    def get_uom_action(self):
        """Return the action dict to open the UoM list view.

        Used by the frontend "+ Add UoM" shortcut button so the user can
        quickly add a new UoM (e.g. 'Isi (3)') without leaving the
        Quick Purchase workflow, then come back and select it.
        """
        self._check_purchase_access()
        # Try to get the standard uom action first
        action = request.env.ref("uom.product_uom_form_action", raise_if_not_found=False)
        if action:
            return action.read()[0]
        # Fallback: return a minimal action dict
        return {
            "type": "ir.actions.act_window",
            "name": "Units of Measure",
            "res_model": "uom.uom",
            "view_mode": "list,form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # 8. Sync sessions across devices (Replaces old load/save/clear)
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/sync_sessions",
        type="json",
        auth="user",
    )
    def sync_sessions(self, sessions, active_session_id=None):
        self._check_purchase_access()
        request.env["quick.purchase.session"].sync_sessions(sessions, active_session_id)
        return True

    @http.route(
        "/andykanoz_quick_purchase/load_sessions",
        type="json",
        auth="user",
    )
    def load_sessions(self):
        self._check_purchase_access()
        return request.env["quick.purchase.session"].load_sessions()

    @http.route(
        "/andykanoz_quick_purchase/clear_session",
        type="json",
        auth="user",
    )
    def clear_session(self, session_id):
        self._check_purchase_access()
        return request.env["quick.purchase.session"].clear_session(session_id)

    @http.route(
        "/andykanoz_quick_purchase/get_category_action",
        type="json",
        auth="user",
    )
    def get_category_action(self):
        self._check_purchase_access()
        action = request.env.ref("product.product_category_action_form", raise_if_not_found=False)
        if action:
            return action.read()[0]
        return {
            "type": "ir.actions.act_window",
            "name": "Product Categories",
            "res_model": "product.category",
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "target": "new",
        }

    @http.route(
        "/andykanoz_quick_purchase/get_public_category_action",
        type="json",
        auth="user",
    )
    def get_public_category_action(self):
        self._check_purchase_access()
        if "product.public.category" not in request.env:
            raise UserError(_("Public categories are not available in this database."))
        action = request.env.ref("website_sale.product_public_category_action", raise_if_not_found=False)
        if action:
            return action.read()[0]
        return {
            "type": "ir.actions.act_window",
            "name": "Public Categories",
            "res_model": "product.public.category",
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "target": "new",
        }

    # ------------------------------------------------------------------
    # 8. Reload UoM options for a specific product
    #    (used after user adds a new UoM and comes back)
    # ------------------------------------------------------------------

    @http.route(
        "/andykanoz_quick_purchase/refresh_uoms",
        type="json",
        auth="user",
    )
    def refresh_uoms(self, product_id):
        self._check_purchase_access()
        product = request.env["product.product"].browse(int(product_id))
        if not product.exists() or not product.uom_id:
            return {"uom_options": []}
        return {
            "uom_options": self._get_uoms_for_category(
                product.uom_id.category_id.id
            ),
        }

