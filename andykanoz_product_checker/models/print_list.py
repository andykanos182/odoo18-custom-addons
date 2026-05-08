# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductCheckerPrintList(models.Model):
    _name = 'product.checker.print.list'
    _description = 'Product Checker Print List Item'
    _order = 'create_date desc'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'unique_product_per_user',
            'unique(product_tmpl_id, user_id)',
            'This product is already in your print list.',
        ),
    ]

    @api.model
    def get_my_print_list(self):
        """Return current user's print list items with product info."""
        items = self.search([('user_id', '=', self.env.user.id)])
        result = []
        for item in items:
            product = item.product_tmpl_id
            result.append({
                'id': item.id,
                'product_tmpl_id': product.id,
                'name': product.name,
                'default_code': product.default_code or '',
                'barcode': product.barcode or '',
                'image_url': '/web/image/product.template/%s/image_128' % product.id,
            })
        return result

    @api.model
    def add_to_my_list(self, product_tmpl_id):
        """Add a product to current user's print list. Returns updated list."""
        if not product_tmpl_id:
            return {'success': False, 'error': _('Product ID is required')}

        existing = self.search([
            ('user_id', '=', self.env.user.id),
            ('product_tmpl_id', '=', int(product_tmpl_id)),
        ], limit=1)
        if existing:
            return {
                'success': True,
                'already_exists': True,
                'list': self.get_my_print_list(),
            }

        try:
            self.create({
                'product_tmpl_id': int(product_tmpl_id),
                'user_id': self.env.user.id,
            })
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return {
            'success': True,
            'already_exists': False,
            'list': self.get_my_print_list(),
        }

    @api.model
    def remove_from_my_list(self, item_id):
        """Remove an item from current user's print list."""
        item = self.search([
            ('id', '=', int(item_id)),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if item:
            item.unlink()
        return {'success': True, 'list': self.get_my_print_list()}

    @api.model
    def clear_my_list(self):
        """Clear all items from current user's print list."""
        items = self.search([('user_id', '=', self.env.user.id)])
        items.unlink()
        return {'success': True, 'list': []}

    @api.model
    def get_print_action(self):
        """
        Return the action to open Odoo's native product.label.layout wizard
        with current user's print list products preloaded.
        """
        items = self.search([('user_id', '=', self.env.user.id)])
        if not items:
            return {'success': False, 'error': _('Print list is empty')}

        product_ids = items.mapped('product_tmpl_id').ids

        action = self.env['ir.actions.actions']._for_xml_id(
            'product.action_open_label_layout'
        )
        action['context'] = {
            'default_product_tmpl_ids': product_ids,
            'active_model': 'product.template',
            'active_ids': product_ids,
        }
        return {'success': True, 'action': action}
