# -*- coding: utf-8 -*-
"""Purchase Mobile — JSON-RPC API endpoints.

Phase 2 endpoints:
    POST /andykanoz_purchase_mobile/api/vendors
    POST /andykanoz_purchase_mobile/api/products/search
    POST /andykanoz_purchase_mobile/api/pos/list
    POST /andykanoz_purchase_mobile/api/po/get

All endpoints use Odoo's JSON-RPC dispatch (type='json'). Client sends a
POST with body { jsonrpc: '2.0', method: 'call', params: {...} } and
receives { jsonrpc: '2.0', id: N, result: {...} }. The method below
returns the raw dict for `result`.
"""

import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PurchaseMobileApi(http.Controller):
    """JSON-RPC endpoints for the Purchase Mobile OWL client."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _serialize_uom_options(self, product):
        """Return all UoM options the user can pick for a product line.

        Strategy: list every UoM that shares the product's UoM category.
        Odoo's purchase.order.line restricts product_uom to the
        product's category at write time (raise on mismatch), so we
        match that constraint client-side by only offering compatible
        UoMs. The product's default uom_id and uom_po_id are always
        included even if the broader category fetch fails.
        """
        Uom = request.env['uom.uom']
        uoms = Uom
        category = product.uom_id.category_id
        if category:
            uoms = Uom.search([
                ('category_id', '=', category.id),
                ('active', '=', True),
            ], order='factor desc')
        # Defensive: fall back to just the product's own UoM(s) if the
        # category search returned nothing (data error or unconfigured
        # category).
        if not uoms:
            uoms = product.uom_id | product.uom_po_id
        return [
            {'id': u.id, 'name': u.name}
            for u in uoms
        ]

    def _has_product_expiry(self):
        """Check whether the product_expiry module is installed.

        We detect it via the presence of the `use_expiration_date` field
        on product.template, which is added by product_expiry. This lets
        the module degrade gracefully when expiry tracking is not active.
        """
        return 'use_expiration_date' in request.env['product.template']._fields

    def _get_expiry_warning_days(self):
        """Return the threshold (in days) below which an expiry date is
        considered "near" — used by the frontend to color the badge red.
        Configured via ir.config_parameter; default 60.
        """
        ICP = request.env['ir.config_parameter'].sudo()
        raw = ICP.get_param(
            'andykanoz_purchase_mobile.expiry_warning_days', '60'
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 60

    def _requires_expiry(self, product, has_expiry_module=None):
        """Return True if this product should prompt for an expiry date.

        Rules:
          1. If product_expiry is installed AND the product has
             use_expiration_date = True, then yes.
          2. Else if x_requires_expiry (our custom fallback flag) is set,
             then yes.
          3. Otherwise, no.
        """
        if has_expiry_module is None:
            has_expiry_module = self._has_product_expiry()
        tmpl = product.product_tmpl_id
        if has_expiry_module and getattr(tmpl, 'use_expiration_date', False):
            return True
        return bool(getattr(tmpl, 'x_requires_expiry', False))

    def _get_unit_price(self, product, partner_id=None):
        """Three-tier price fallback matching andykanoz_quick_purchase.

        1. Most recent confirmed PO line for this product + vendor.
        2. product.supplierinfo (seller_ids) entry for this vendor.
        3. product.standard_price as the final fallback.
        """
        if partner_id:
            PoLine = request.env['purchase.order.line']
            recent = PoLine.search(
                [
                    ('product_id', '=', product.id),
                    ('order_id.partner_id', '=', partner_id),
                    ('order_id.state', 'in', ['purchase', 'done']),
                ],
                limit=1,
                order='create_date desc',
            )
            if recent:
                return recent.price_unit

            seller = product.seller_ids.filtered(
                lambda s: s.partner_id.id == partner_id
            )
            if seller:
                return seller[0].price

        return product.standard_price

    def _serialize_partner(self, partner):
        """Compact partner representation for list views."""
        if not partner:
            return None
        return {
            'id': partner.id,
            'name': partner.name,
            'display_name': partner.display_name,
            'email': partner.email or '',
            'phone': partner.phone or '',
            'city': partner.city or '',
        }

    def _serialize_currency(self, currency):
        if not currency:
            return None
        return {
            'id': currency.id,
            'name': currency.name,
            'symbol': currency.symbol or '',
            'decimal_places': currency.decimal_places,
        }

    # ------------------------------------------------------------------
    # Endpoint: vendors
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/vendors',
        type='json',
        auth='user',
    )
    def vendors(self, query='', limit=20):
        """Search vendors (suppliers) by name / email / phone.

        Uses name_search with the `res_partner_search_mode='supplier'`
        context — this matches standard Odoo PO vendor selection and
        includes partners with supplier_rank = 0 (which are excluded by
        a naive domain-based search). This is the same fix applied to
        andykanoz_quick_purchase.
        """
        Partner = request.env['res.partner']
        tuples = Partner.with_context(
            res_partner_search_mode='supplier'
        ).name_search(
            name=query or '',
            args=[],
            operator='ilike',
            limit=limit,
        )
        partner_ids = [t[0] for t in tuples]
        partners = Partner.browse(partner_ids)
        return {
            'vendors': [self._serialize_partner(p) for p in partners],
            'count': len(partners),
        }

    # ------------------------------------------------------------------
    # Endpoint: products/search
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/products/search',
        type='json',
        auth='user',
    )
    def products_search(self, query='', limit=20, vendor_id=None):
        """Search purchasable products by barcode, SKU, or name.

        If `vendor_id` is provided, the response includes `unit_price`
        resolved via the three-tier fallback (recent PO line → seller
        info → standard_price). Without a vendor, only `standard_price`
        is returned as `unit_price`.

        Packaging barcode handling:
          When `query` exactly matches a `product.packaging.barcode`,
          we ALSO surface that product (even if its own product.barcode
          doesn't match) and tag the response with
          `matched_packaging_id` pointing at the specific packaging row.
          The frontend uses that hint to auto-select the packaging on
          the new line and convert the qty (1 box = packaging.qty units).
          This is what makes "scan the box, not the can" work for the
          warehouse team.
        """
        Product = request.env['product.product']

        # ---- Packaging-barcode probe (exact match only) ----
        # We only attempt this when query is non-empty and looks like
        # it could be a barcode. We don't restrict to digits-only
        # because some private codes are alphanumeric (e.g. 'BOX-COKE-24').
        # Exact match keeps it cheap; a partial match against packaging
        # barcodes wouldn't be useful (users either scan or they don't).
        matched_pkg = request.env['product.packaging']
        if query:
            matched_pkg = request.env['product.packaging'].search(
                [('barcode', '=', query)], limit=1
            )

        domain = [('purchase_ok', '=', True)]
        if query:
            domain = [
                '&',
                ('purchase_ok', '=', True),
                '|', '|',
                ('barcode', '=', query),
                ('default_code', 'ilike', query),
                ('name', 'ilike', query),
            ]

        products = Product.search(domain, limit=limit)

        # If a packaging matched, ensure its product is in the result
        # set even when the regular search domain didn't catch it. We
        # prepend it (most-relevant-first) and dedupe by id.
        if matched_pkg and matched_pkg.product_id:
            pkg_product = matched_pkg.product_id
            if pkg_product.purchase_ok:
                if pkg_product.id not in products.ids:
                    products = pkg_product | products
                else:
                    # Already in results — move to front by reordering.
                    products = pkg_product | (products - pkg_product)

        has_expiry = self._has_product_expiry()

        results = []
        for p in products:
            unit_price = self._get_unit_price(p, partner_id=vendor_id)
            # If this product is the one whose packaging barcode
            # matched the query, tell the frontend which specific
            # packaging row caused the match. Otherwise, this is None
            # and the frontend treats it as a regular unit-barcode hit.
            this_match = (
                matched_pkg.id
                if matched_pkg and matched_pkg.product_id.id == p.id
                else None
            )
            results.append({
                'id': p.id,
                'name': p.name,
                'display_name': p.display_name,
                'default_code': p.default_code or '',
                'barcode': p.barcode or '',
                'image_url': (
                    '/web/image/product.product/%s/image_128' % p.id
                ),
                'uom_id': {
                    'id': p.uom_id.id,
                    'name': p.uom_id.name,
                },
                'uom_po_id': {
                    'id': p.uom_po_id.id,
                    'name': p.uom_po_id.name,
                },
                # Full UoM dropdown for this line. Filtered to the
                # product's category so the user can't accidentally
                # pick an incompatible UoM (Odoo would reject on save).
                'uom_options': self._serialize_uom_options(p),
                'packagings': [
                    {
                        'id': pkg.id,
                        'name': pkg.name,
                        'qty': pkg.qty,
                        'barcode': pkg.barcode or '',
                    }
                    for pkg in p.packaging_ids
                ],
                'standard_price': p.standard_price,
                'unit_price': unit_price,
                'requires_expiry': self._requires_expiry(p, has_expiry),
                # Phase 8b: id of the product.packaging whose barcode
                # matched the search query (if any). The frontend uses
                # this to pre-select that packaging on a freshly added
                # line and to compute qty as packaging.qty * boxes.
                'matched_packaging_id': this_match,
            })
        return {
            'products': results,
            'count': len(results),
            'has_product_expiry_module': has_expiry,
            'expiry_warning_days': self._get_expiry_warning_days(),
        }

    # ------------------------------------------------------------------
    # Endpoint: pos/list
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/pos/list',
        type='json',
        auth='user',
    )
    def pos_list(self, state='draft', mobile_only=False, limit=50):
        """List purchase orders filtered by state.

        Args:
            state: single state string or list. Default 'draft'.
                   Pass None / '' / [] to skip the filter.
            mobile_only: if True, only return POs created via this app
                         (x_created_via_mobile = True).
            limit: max rows returned.
        """
        domain = []
        if state:
            state_list = state if isinstance(state, list) else [state]
            domain.append(('state', 'in', state_list))
        if mobile_only:
            domain.append(('x_created_via_mobile', '=', True))

        PO = request.env['purchase.order']
        orders = PO.search(domain, limit=limit, order='create_date desc')
        state_selection = dict(PO._fields['state'].selection)

        results = []
        for po in orders:
            results.append({
                'id': po.id,
                'name': po.name,
                'state': po.state,
                'state_label': state_selection.get(po.state, po.state),
                'partner': self._serialize_partner(po.partner_id),
                'date_order': (
                    fields.Datetime.to_string(po.date_order)
                    if po.date_order else ''
                ),
                'amount_untaxed': po.amount_untaxed,
                'amount_total': po.amount_total,
                'line_count': len(po.order_line),
                'created_via_mobile': po.x_created_via_mobile,
                'currency': self._serialize_currency(po.currency_id),
            })
        return {'orders': results, 'count': len(results)}

    # ------------------------------------------------------------------
    # Endpoint: po/get
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/po/get',
        type='json',
        auth='user',
    )
    def po_get(self, po_id):
        """Return a single purchase order with all lines expanded."""
        if not po_id:
            return {'error': 'missing_po_id'}

        PO = request.env['purchase.order']
        po = PO.browse(int(po_id))
        if not po.exists():
            return {'error': 'not_found', 'po_id': po_id}

        has_expiry = self._has_product_expiry()
        state_selection = dict(PO._fields['state'].selection)

        lines = []
        for line in po.order_line:
            product = line.product_id
            pkg = line.product_packaging_id
            lines.append({
                'id': line.id,
                'sequence': line.sequence,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'display_name': product.display_name,
                    'default_code': product.default_code or '',
                    'image_url': (
                        '/web/image/product.product/%s/image_128'
                        % product.id
                    ),
                },
                'name': line.name or '',
                'product_qty': line.product_qty,
                'product_uom': {
                    'id': line.product_uom.id,
                    'name': line.product_uom.name,
                },
                # Phase "uom-fix": ship dropdown options for existing
                # lines too, otherwise editing an existing PO leaves
                # the UoM and Packaging selects stuck on a single value.
                'uom_options': self._serialize_uom_options(product),
                'packagings': [
                    {
                        'id': pkg_opt.id,
                        'name': pkg_opt.name,
                        'qty': pkg_opt.qty,
                        'barcode': pkg_opt.barcode or '',
                    }
                    for pkg_opt in product.packaging_ids
                ],
                'product_packaging': (
                    {
                        'id': pkg.id,
                        'name': pkg.name,
                        'qty': pkg.qty,
                    } if pkg else None
                ),
                'product_packaging_qty': line.product_packaging_qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'x_expected_expiry_date': (
                    fields.Date.to_string(line.x_expected_expiry_date)
                    if line.x_expected_expiry_date else None
                ),
                'requires_expiry': self._requires_expiry(product, has_expiry),
            })

        return {
            'order': {
                'id': po.id,
                'name': po.name,
                'state': po.state,
                'state_label': state_selection.get(po.state, po.state),
                'partner': self._serialize_partner(po.partner_id),
                'date_order': (
                    fields.Datetime.to_string(po.date_order)
                    if po.date_order else ''
                ),
                'amount_untaxed': po.amount_untaxed,
                'amount_total': po.amount_total,
                'created_via_mobile': po.x_created_via_mobile,
                'currency': self._serialize_currency(po.currency_id),
                'lines': lines,
            },
            'has_product_expiry_module': has_expiry,
            'expiry_warning_days': self._get_expiry_warning_days(),
        }

    # ------------------------------------------------------------------
    # Internal helper: serialize one incoming line dict into Odoo
    # purchase.order.line values. Used by po_save for both create-new
    # and update-existing paths so field coercion stays consistent.
    # ------------------------------------------------------------------

    def _build_line_vals(self, line):
        """Return a dict of purchase.order.line field values.

        Expects keys: product_id, product_qty, product_uom_id,
        product_packaging_id (optional), product_packaging_qty (optional),
        price_unit, expected_expiry_date (optional, ISO date string).
        """
        vals = {
            'product_id': line['product_id'],
            'product_qty': line.get('product_qty') or 0.0,
            'price_unit': line.get('price_unit') or 0.0,
        }
        uom_id = line.get('product_uom_id')
        if uom_id:
            vals['product_uom'] = uom_id
        pkg_id = line.get('product_packaging_id')
        # False clears the field, None leaves it out. We want explicit
        # clear when the client sent null so users can remove a packaging.
        if 'product_packaging_id' in line:
            vals['product_packaging_id'] = pkg_id or False
        if 'product_packaging_qty' in line:
            vals['product_packaging_qty'] = line.get('product_packaging_qty') or 0.0
        if 'expected_expiry_date' in line:
            vals['x_expected_expiry_date'] = line.get('expected_expiry_date') or False
        return vals

    # ------------------------------------------------------------------
    # Endpoint: po/save
    #
    # Creates a new draft PO when po_id is null, otherwise updates the
    # existing one. Only draft POs can be updated — once confirmed, edits
    # must go through the desktop Odoo UI's standard PO workflow.
    #
    # New POs get the custom "MP00xxx" sequence and x_created_via_mobile
    # = True, so reports can distinguish mobile-born orders from ones
    # created via the regular desktop form.
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/po/save',
        type='json',
        auth='user',
    )
    def po_save(self, po_id=None, vendor_id=None, lines=None):
        lines = lines or []

        if not vendor_id:
            return {'error': 'missing_vendor'}

        # ---- Create path ----
        if not po_id:
            seq = request.env['ir.sequence'].next_by_code(
                'andykanoz.purchase.mobile'
            ) or '/'
            line_cmds = [(0, 0, self._build_line_vals(l)) for l in lines]
            po = request.env['purchase.order'].create({
                'name': seq,
                'partner_id': int(vendor_id),
                'x_created_via_mobile': True,
                'order_line': line_cmds,
            })
            _logger.info(
                "[purchase_mobile] Created PO %s (id=%s) via mobile",
                po.name, po.id,
            )
            # Return the freshly saved order via po_get for consistency
            # of the response shape between create and update.
            return self.po_get(po_id=po.id)

        # ---- Update path ----
        po = request.env['purchase.order'].browse(int(po_id))
        if not po.exists():
            return {'error': 'not_found', 'po_id': po_id}
        if po.state != 'draft':
            return {'error': 'not_draft', 'state': po.state}

        # Step 1: delete removed lines.
        incoming_ids = {int(l['id']) for l in lines if l.get('id')}
        for existing in po.order_line:
            if existing.id not in incoming_ids:
                existing.unlink()

        # Step 2: update + create.
        POLine = request.env['purchase.order.line']
        for line in lines:
            line_id = line.get('id')
            vals = self._build_line_vals(line)
            if line_id:
                target = POLine.browse(int(line_id))
                if target.exists() and target.order_id.id == po.id:
                    target.write(vals)
                else:
                    # Fallback: id sent but not ours. Create new.
                    vals['order_id'] = po.id
                    POLine.create(vals)
            else:
                vals['order_id'] = po.id
                POLine.create(vals)

        # Step 3: vendor change (rare — UI locks vendor after first
        # line, but support it anyway for future flexibility).
        if po.partner_id.id != int(vendor_id):
            po.write({'partner_id': int(vendor_id)})

        _logger.info(
            "[purchase_mobile] Updated PO %s (id=%s)", po.name, po.id
        )
        return self.po_get(po_id=po.id)

    # ------------------------------------------------------------------
    # Endpoint: po/confirm
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/po/confirm',
        type='json',
        auth='user',
    )
    def po_confirm(self, po_id):
        if not po_id:
            return {'error': 'missing_po_id'}
        po = request.env['purchase.order'].browse(int(po_id))
        if not po.exists():
            return {'error': 'not_found', 'po_id': po_id}
        if po.state != 'draft':
            return {'error': 'not_draft', 'state': po.state}
        if not po.order_line:
            return {'error': 'no_lines'}
        po.button_confirm()
        _logger.info(
            "[purchase_mobile] Confirmed PO %s (id=%s), new state=%s",
            po.name, po.id, po.state,
        )
        return self.po_get(po_id=po.id)

    # ------------------------------------------------------------------
    # Endpoint: po/delete
    #
    # Only draft POs can be deleted through the mobile app. For any
    # other state, the user must use the desktop workflow (cancel,
    # then unlink) which invokes proper audit trails.
    # ------------------------------------------------------------------

    @http.route(
        '/andykanoz_purchase_mobile/api/po/delete',
        type='json',
        auth='user',
    )
    def po_delete(self, po_id):
        if not po_id:
            return {'error': 'missing_po_id'}
        po = request.env['purchase.order'].browse(int(po_id))
        if not po.exists():
            return {'error': 'not_found', 'po_id': po_id}
        if po.state != 'draft':
            return {'error': 'not_draft', 'state': po.state}
        name = po.name
        po.unlink()
        _logger.info("[purchase_mobile] Deleted draft PO %s", name)
        return {'success': True, 'deleted_name': name}
