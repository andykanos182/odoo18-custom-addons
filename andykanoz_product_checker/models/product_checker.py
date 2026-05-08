# -*- coding: utf-8 -*-
import time
from odoo import models, api, fields, _
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class ProductCheckerPrintList(models.Model):
    _name = 'product.checker.print.list'
    _description = 'Product Checker Print Label List'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        default=lambda self: self.env.user, ondelete='cascade', index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True,
        ondelete='cascade', index=True,
    )

    _sql_constraints = [
        ('unique_user_product', 'unique(user_id, product_tmpl_id)',
         'This product is already in your print list.'),
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def update_product_image(self, product_tmpl_id, image_base64):
        """Update product image from base64 string.

        Args:
            product_tmpl_id (int): product.template ID
            image_base64 (str): base64-encoded image data (tanpa prefix 'data:image/...;base64,')
        Returns:
            dict: {success: True, image_url: str} atau {success: False, error: str}
        """
        try:
            product = self.env['product.template'].browse(product_tmpl_id)
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            product.write({'image_1920': image_base64})
            # Tambahkan timestamp buster agar browser tidak cache gambar lama
            image_url = '/web/image/product.template/%s/image_1024?t=%s' % (
                product_tmpl_id, int(time.time())
            )
            return {'success': True, 'image_url': image_url}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def update_standard_price(self, product_tmpl_id, new_cost, pricelist_id=None):
        """Update standard price safely (Cost)."""
        try:
            product = self.env['product.template'].browse(product_tmpl_id)
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            # Gunakan context company dari user saat ini agar JSONB tersimpan di company yang benar.
            # Tambahkan disable_auto_svl=True agar write tidak diblokir oleh stock_account saat cost_method FIFO/AVCO.
            product_with_ctx = product.with_company(self.env.company).sudo().with_context(disable_auto_svl=True)
            product_with_ctx.write({'standard_price': new_cost})
            
            # Jika product memiliki varian lebih dari 1, Odoo secara native mengabaikan write standard_price 
            # pada level template, sehingga kita harus push manual ke setiap varian.
            if product.product_variant_ids:
                product.product_variant_ids.with_company(self.env.company).sudo().with_context(disable_auto_svl=True).write({
                    'standard_price': new_cost
                })
            
            # Invalidate cache to ensure subsequent price computation uses the new cost
            product.invalidate_recordset(['standard_price'])
            if product.product_variant_ids:
                product.product_variant_ids.invalidate_recordset(['standard_price'])

            fresh_info = product._get_checker_info(pricelist_id=pricelist_id)
            
            return {
                'success': True, 
                'new_cost': fresh_info.get('standard_price'),
                'new_price': fresh_info.get('price'),
                'data': fresh_info
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def update_quantity_on_hand(self, product_tmpl_id, new_quantity):
        """Update stock quantity for the default variant in the company's main warehouse."""
        try:
            product_tmpl = self.browse(product_tmpl_id).exists()
            if not product_tmpl:
                return {'success': False, 'error': 'Product not found'}
            if not product_tmpl.product_variant_id:
                return {'success': False, 'error': 'No product variant found'}
                
            product = product_tmpl.product_variant_id
            company = self.env.company
            
            # Find the main warehouse for the company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
            if not warehouse:
                return {'success': False, 'error': 'No warehouse found for this company'}
                
            location_id = warehouse.lot_stock_id
            
            # Create a stock.quant in inventory mode
            quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'location_id': location_id.id,
                'inventory_quantity': float(new_quantity),
            })
            quant.action_apply_inventory()
            
            return {'success': True, 'new_qty': product.qty_available}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def search_product_by_barcode(self, barcode, pricelist_id=None):
        """
        Search product.template by barcode or default_code or name.
        Returns dict with product info or {'found': False} if not found.
        """
        if not barcode:
            return {'found': False, 'error': _('Barcode is empty')}

        barcode = barcode.strip()

        # Search by barcode first, then by default_code, then by name contains
        product = self.search([('barcode', '=', barcode)], limit=1)
        if not product:
            product = self.search([('default_code', '=', barcode)], limit=1)
        if not product:
            # Fallback: check variants (product.product) barcode
            variant = self.env['product.product'].search([
                ('barcode', '=', barcode)
            ], limit=1)
            if variant:
                product = variant.product_tmpl_id
        if not product:
            # Fallback: name contains
            product = self.search([('name', 'ilike', barcode)], limit=1)

        if not product:
            return {'found': False, 'searched': barcode}

        return {
            'found': True,
            'data': product._get_checker_info(pricelist_id=pricelist_id),
        }

    @api.model
    def search_products_for_panel(self, query='', pricelist_id=None, offset=0, limit=50, filter_domain=None):
        """
        Paginated product list for the left-side Product List drawer.

        Search semantics mirror Odoo's standard product.template search:
        matches on name, default_code, and barcode (ilike). Only active
        records are returned (default Odoo active-test context applies).

        Args:
            query (str): Free-text filter. Empty string returns all active products.
            pricelist_id (int|False): Pricelist used to compute each product's 'price'.
            offset (int): Pagination offset.
            limit (int): Max products to return (default 50).
            filter_domain (str|list): Optional domain from the Custom Filter
                dialog (Domain Selector). Can be a domain string such as
                "[('sale_ok','=',True)]" or an already-parsed list. Combined
                with the text query using AND.

        Returns:
            dict: {
                'products': [ ... ],
                'total': int,
                'has_more': bool,
                'offset': int,
                'limit': int,
                'filter_count': int,   # number of leaf conditions in filter_domain
            }
        """
        query = (query or '').strip()
        text_domain = []
        if query:
            text_domain = [
                '|', '|',
                ('name', 'ilike', query),
                ('default_code', 'ilike', query),
                ('barcode', 'ilike', query),
            ]

        # Parse the Custom Filter domain (string from Domain Selector or list).
        extra_domain = []
        filter_count = 0
        if filter_domain:
            if isinstance(filter_domain, str):
                s = filter_domain.strip()
                if s and s != '[]':
                    try:
                        # NOTE: do NOT inject raw `datetime` / `relativedelta`
                        # modules here — Odoo 18's safe_eval rejects bare
                        # modules with a hard error. The Domain Selector
                        # dialog builds plain tuple literals (no datetime
                        # expressions), so a minimal context is enough.
                        extra_domain = safe_eval(s, {
                            'True': True,
                            'False': False,
                            'None': None,
                        }) or []
                    except Exception as e:
                        # Log so misparses don't silently vanish
                        import logging
                        logging.getLogger(__name__).warning(
                            "[product_checker] Failed to parse filter domain: %r \u2014 %s",
                            s, e,
                        )
                        extra_domain = []
            elif isinstance(filter_domain, (list, tuple)):
                extra_domain = list(filter_domain)

            # Count leaves (tuples of length 3) for the UI badge
            for leaf in extra_domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    filter_count += 1

        # Combine text query with custom filter using AND
        final_domain = expression.AND([text_domain, extra_domain])

        # Debug trace — prints exactly what the backend sees so we can
        # verify the filter is being received and applied.
        import logging
        _log = logging.getLogger(__name__)
        _log.info(
            "[product_checker][panel] filter_domain=%r parsed=%r final=%r",
            filter_domain, extra_domain, final_domain,
        )

        try:
            limit = max(1, min(int(limit or 50), 200))
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = max(0, int(offset or 0))
        except (TypeError, ValueError):
            offset = 0

        total = self.search_count(final_domain)
        products = self.search(final_domain, offset=offset, limit=limit, order='name asc')
        _log.info(
            "[product_checker][panel] total=%d returned=%d offset=%d limit=%d",
            total, len(products), offset, limit,
        )

        # Resolve pricelist once (optional)
        pricelist = False
        if pricelist_id:
            try:
                pricelist = self.env['product.pricelist'].browse(int(pricelist_id)).exists()
            except (TypeError, ValueError):
                pricelist = False

        result = []
        for p in products:
            variant = p.product_variant_id

            # Sales price via pricelist (fallback: list_price)
            price = p.list_price
            if pricelist and variant:
                try:
                    price = pricelist._get_product_price(variant, 1.0)
                except Exception:
                    price = p.list_price

            # Stock on hand from default variant
            qty_on_hand = variant.qty_available if variant else 0.0

            result.append({
                'id': p.id,
                'name': p.name,
                'default_code': p.default_code or '',
                'barcode': p.barcode or '',
                'image_url': '/web/image/product.template/%s/image_128' % p.id,
                'standard_price': p.standard_price,
                'price': price,
                'qty_on_hand': qty_on_hand,
                'uom_name': p.uom_id.name if p.uom_id else '',
                'currency_symbol': p.currency_id.symbol or '',
                'currency_position': p.currency_id.position or 'before',
            })

        return {
            'products': result,
            'total': total,
            'has_more': (offset + limit) < total,
            'offset': offset,
            'limit': limit,
            'filter_count': filter_count,
        }

    def _get_checker_info(self, pricelist_id=None):
        """Return formatted product info for the checker page."""
        self.ensure_one()

        # Get price from pricelist
        price = self.list_price
        pricelist_name = _('Sales Price (Default)')
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(int(pricelist_id)).exists()
            if pricelist:
                # Use _get_product_price for a single product template
                try:
                    price = pricelist._get_product_price(
                        self.product_variant_id, 1.0
                    )
                    pricelist_name = pricelist.name
                except Exception:
                    # Fallback if method signature differs
                    price = self.list_price

        # Stock on hand from default product variant
        qty_on_hand = 0.0
        if self.product_variant_id:
            qty_on_hand = self.product_variant_id.qty_available

        # Image URL - use product.template image with cache buster
        unique_ts = str(int(self.write_date.timestamp())) if self.write_date else ''
        image_url = '/web/image/product.template/%s/image_1024?unique=%s' % (self.id, unique_ts)

        # Ecommerce categories
        ecom_categs = []
        if hasattr(self, 'public_categ_ids'):
            ecom_categs = [{'id': c.id, 'name': c.display_name or c.name} for c in self.public_categ_ids]

        # Product Tags
        p_tags = []
        if hasattr(self, 'product_tag_ids'):
            p_tags = [{'id': t.id, 'name': t.name} for t in self.product_tag_ids]

        is_published = False
        if 'is_published' in self._fields:
            is_published = self.is_published

        # Inline-toggle fields shown on the product card.
        # Guarded with _fields check so the module stays robust if a
        # dependency is missing (e.g. point_of_sale for available_in_pos).
        sale_ok = bool(self.sale_ok) if 'sale_ok' in self._fields else False
        purchase_ok = bool(self.purchase_ok) if 'purchase_ok' in self._fields else False
        is_storable = bool(self.is_storable) if 'is_storable' in self._fields else False
        available_in_pos = bool(self.available_in_pos) if 'available_in_pos' in self._fields else False

        return {
            'id': self.id,
            'name': self.name,
            'default_code': self.default_code or '',
            'barcode': self.barcode or '',
            'list_price': self.list_price,
            'standard_price': self.standard_price,
            'price': price,
            'pricelist_name': pricelist_name,
            'qty_on_hand': qty_on_hand,
            'uom_name': self.uom_id.name if self.uom_id else '',
            'categ_id': self.categ_id.id,
            'categ_name': self.categ_id.complete_name or self.categ_id.name,
            'image_url': image_url,
            'is_published': is_published,
            'sale_ok': sale_ok,
            'purchase_ok': purchase_ok,
            'is_storable': is_storable,
            'available_in_pos': available_in_pos,
            'public_categ_ids': ecom_categs,
            'product_tag_ids': p_tags,
            'currency_symbol': self.currency_id.symbol or '',
            'currency_position': self.currency_id.position or 'before',
        }

    @api.model
    def get_checker_config(self):
        """Return default pricelist, available pricelists, and currency."""
        pricelists = self.env['product.pricelist'].search_read(
            [], ['id', 'name', 'currency_id']
        )
        # Default pricelist: first one or user's company default
        default_pricelist_id = False
        if pricelists:
            default_pricelist_id = pricelists[0]['id']

        categories = self.env['product.category'].search_read(
            [], ['id', 'complete_name'], limit=200
        )

        public_categories = []
        if 'product.public.category' in self.env:
            pub_cats = self.env['product.public.category'].search([], limit=200)
            public_categories = [{'id': c.id, 'name': c.name, 'display_name': c.display_name} for c in pub_cats]

        product_tags = []
        if 'product.tag' in self.env:
            p_tags = self.env['product.tag'].search([], limit=200)
            product_tags = [{'id': t.id, 'name': t.name} for t in p_tags]

        # Load current user's print list
        print_list_items = self.env['product.checker.print.list'].search_read(
            [('user_id', '=', self.env.user.id)],
            ['product_tmpl_id'],
        )
        print_list = []
        for item in print_list_items:
            if item['product_tmpl_id']:
                tmpl_id = item['product_tmpl_id'][0]
                product = self.browse(tmpl_id).exists()
                if product:
                    print_list.append({
                        'id': product.id,
                        'name': product.name,
                        'default_code': product.default_code or '',
                        'barcode': product.barcode or '',
                        'image_url': '/web/image/product.template/%s/image_128' % product.id,
                    })

        return {
            'pricelists': pricelists,
            'default_pricelist_id': default_pricelist_id,
            'categories': categories,
            'public_categories': public_categories,
            'product_tags': product_tags,
            'print_list': print_list,
        }

    @api.model
    def quick_create_from_checker(self, vals):
        """
        Create a product.template from checker page.
        """
        if not vals.get('name'):
            return {'success': False, 'error': _('Name is required')}

        create_vals = {
            'name': vals.get('name'),
            'type': 'consu',  # Odoo 18: 'consu' with is_storable=True for stockable
        }

        # Boolean flags — accept client-provided values; if the key is absent
        # from vals, default to True (matches the checker's "default scanned
        # product" semantics). The `_fields` guard keeps the module robust
        # if a dependency (e.g. point_of_sale, website_sale) is missing.
        bool_defaults = {
            'sale_ok': True,
            'purchase_ok': True,
            'is_storable': True,
            'available_in_pos': True,
            'is_published': True,
        }
        for field_name, default_value in bool_defaults.items():
            if field_name not in self._fields:
                continue
            if field_name in vals:
                create_vals[field_name] = bool(vals[field_name])
            else:
                create_vals[field_name] = default_value

        if vals.get('barcode'):
            # Check duplicate barcode
            existing = self.search([('barcode', '=', vals['barcode'])], limit=1)
            if existing:
                return {
                    'success': False,
                    'error': _('Barcode already exists on product: %s') % existing.name,
                }
            create_vals['barcode'] = vals['barcode']

        if vals.get('default_code'):
            create_vals['default_code'] = vals['default_code']
        if vals.get('standard_price') is not None:
            create_vals['standard_price'] = float(vals['standard_price'])
        if vals.get('list_price') is not None:
            create_vals['list_price'] = float(vals['list_price'])
        if vals.get('categ_id'):
            create_vals['categ_id'] = int(vals['categ_id'])
        if vals.get('public_categ_ids') and 'public_categ_ids' in self._fields:
            create_vals['public_categ_ids'] = [(6, 0, [int(x) for x in vals['public_categ_ids']])]
        if vals.get('product_tag_ids') and 'product_tag_ids' in self._fields:
            create_vals['product_tag_ids'] = [(6, 0, [int(x) for x in vals['product_tag_ids']])]

        try:
            product = self.create(create_vals)
        except (UserError, ValidationError) as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': _('Error creating product: %s') % str(e)}

        # Optional: set pricelist item
        if vals.get('pricelist_id') and vals.get('pricelist_price'):
            try:
                self.env['product.pricelist.item'].create({
                    'pricelist_id': int(vals['pricelist_id']),
                    'product_tmpl_id': product.id,
                    'applied_on': '1_product',
                    'compute_price': 'fixed',
                    'fixed_price': float(vals['pricelist_price']),
                })
            except Exception:
                pass  # Don't fail product creation if pricelist item fails

        return {
            'success': True,
            'data': product._get_checker_info(
                pricelist_id=vals.get('pricelist_id')
            ),
        }

    # ============================================================
    # Inline Product Field Toggles (Sales / Purchase / POS / Track Inventory / Published)
    # ============================================================

    # Fields users may toggle inline from the product checker card.
    # This is a whitelist — any other field name is rejected.
    _CHECKER_TOGGLE_ALLOWED_FIELDS = (
        'sale_ok',
        'purchase_ok',
        'available_in_pos',
        'is_storable',
        'is_published',
    )

    @api.model
    def toggle_product_field(self, product_tmpl_id, field_name, value):
        """
        Toggle a single boolean field on product.template. Used by the inline
        switches on the product checker card so users can flip Sales / Purchase
        / POS / Track Inventory / Published without leaving the page.

        Args:
            product_tmpl_id (int): product.template ID
            field_name (str): field name, must be in the allowed whitelist
            value (bool): new boolean value

        Returns:
            dict: {
                'success': bool,
                'error': str (only when success=False),
                'is_track_inventory': bool (only when success=False; True when
                    the error happened while setting is_storable=True, which
                    signals the client to offer the Duplicate & Archive flow),
            }
        """
        if field_name not in self._CHECKER_TOGGLE_ALLOWED_FIELDS:
            return {'success': False, 'error': _('Field not allowed: %s') % field_name}

        product = self.browse(int(product_tmpl_id)).exists()
        if not product:
            return {'success': False, 'error': _('Product not found')}

        if field_name not in product._fields:
            return {
                'success': False,
                'error': _('Field "%s" is not installed on this product (missing module?).') % field_name,
            }

        new_value = bool(value)
        is_ti_enable = (field_name == 'is_storable' and new_value)

        try:
            product.write({field_name: new_value})
            return {'success': True}
        except (UserError, ValidationError) as e:
            return {
                'success': False,
                'error': str(e),
                'is_track_inventory': is_ti_enable,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'is_track_inventory': is_ti_enable,
            }

    @api.model
    def duplicate_for_track_inventory(self, product_tmpl_id, pricelist_id=None):
        """
        Recovery flow when Track Inventory cannot be enabled because the
        product already has transactions (purchases, sales, stock moves).

        Creates a duplicate with is_storable=True and archives the original.
        The original's barcode and internal reference are MOVED to the
        duplicate so scanner workflows keep working. Pricelist items that
        reference the original are also copied to the new product.

        Args:
            product_tmpl_id (int): product.template ID of the original
            pricelist_id (int|False): active pricelist, used for returning
                the computed sales price of the new product

        Returns:
            dict: {'success': bool, 'data': {...}, 'error': str (if failed)}
        """
        original = self.browse(int(product_tmpl_id)).exists()
        if not original:
            return {'success': False, 'error': _('Product not found')}

        original_barcode = original.barcode
        original_default_code = original.default_code

        try:
            with self.env.cr.savepoint():
                # Step 1: clear barcode + default_code from original so the
                # copy can claim them without tripping unique constraints.
                original.write({
                    'barcode': False,
                    'default_code': False,
                })

                # Step 2: duplicate. copy() handles: name, image, category,
                # tags, seller_ids (vendor pricelist), public_categ_ids,
                # most scalar fields. We override to keep the same name
                # (no "(copy)" suffix) and transfer the identifiers.
                new_product = original.copy({
                    'name': original.name,
                    'barcode': original_barcode,
                    'default_code': original_default_code,
                    'is_storable': True,
                    'active': True,
                })

                # Step 3: re-point per-product pricelist items to the new
                # product. Category- or global-level pricelist rules still
                # apply automatically because the new product keeps the
                # same categ_id.
                pricelist_items = self.env['product.pricelist.item'].search([
                    ('product_tmpl_id', '=', original.id),
                ])
                for item in pricelist_items:
                    item.copy({'product_tmpl_id': new_product.id})

                # Step 4: archive the original (Odoo auto-archives variants).
                original.write({'active': False})

            return {
                'success': True,
                'data': new_product._get_checker_info(pricelist_id=pricelist_id),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============================================================
    # Print List Methods
    # ============================================================

    @api.model
    def add_to_print_list(self, product_tmpl_id):
        """Add a product to current user's print list. Idempotent."""
        if not product_tmpl_id:
            return {'success': False, 'error': _('Invalid product')}

        product = self.browse(int(product_tmpl_id)).exists()
        if not product:
            return {'success': False, 'error': _('Product not found')}

        PrintList = self.env['product.checker.print.list']
        existing = PrintList.search([
            ('user_id', '=', self.env.user.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)

        if existing:
            return {
                'success': True,
                'already_exists': True,
                'count': PrintList.search_count([('user_id', '=', self.env.user.id)]),
            }

        try:
            PrintList.create({
                'user_id': self.env.user.id,
                'product_tmpl_id': product.id,
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return {
            'success': True,
            'already_exists': False,
            'count': PrintList.search_count([('user_id', '=', self.env.user.id)]),
            'item': {
                'id': product.id,
                'name': product.name,
                'default_code': product.default_code or '',
                'barcode': product.barcode or '',
                'image_url': '/web/image/product.template/%s/image_128' % product.id,
            },
        }

    @api.model
    def remove_from_print_list(self, product_tmpl_id):
        """Remove a product from current user's print list."""
        PrintList = self.env['product.checker.print.list']
        records = PrintList.search([
            ('user_id', '=', self.env.user.id),
            ('product_tmpl_id', '=', int(product_tmpl_id)),
        ])
        if records:
            records.unlink()
        return {
            'success': True,
            'count': PrintList.search_count([('user_id', '=', self.env.user.id)]),
        }

    @api.model
    def clear_print_list(self):
        """Clear all items from current user's print list."""
        PrintList = self.env['product.checker.print.list']
        PrintList.search([('user_id', '=', self.env.user.id)]).unlink()
        return {'success': True, 'count': 0}

    @api.model
    def get_print_list_action(self):
        """
        Return an action to open Odoo's built-in product.label.layout wizard
        with current user's print list products.
        """
        PrintList = self.env['product.checker.print.list']
        items = PrintList.search([('user_id', '=', self.env.user.id)])

        if not items:
            return {'success': False, 'error': _('Print list is empty')}

        product_tmpl_ids = items.mapped('product_tmpl_id').ids

        # Return action to open the label layout wizard
        return {
            'success': True,
            'action': {
                'name': _('Print Product Labels'),
                'type': 'ir.actions.act_window',
                'res_model': 'product.label.layout',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'default_product_tmpl_ids': product_tmpl_ids,
                    'active_model': 'product.template',
                    'active_ids': product_tmpl_ids,
                },
            },
        }
