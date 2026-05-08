# -*- coding: utf-8 -*-
from odoo import models, api, fields, _


class ProductCheckerSavedFilter(models.Model):
    """
    Per-user saved filters for the Product Checker drawer.

    Each record stores a named combination of the text search query and the
    Custom Filter (Domain Selector) domain. Users can flag one filter as
    their default so it auto-applies the next time the drawer is opened.
    """
    _name = 'andykanoz_product_checker.saved_filter'
    _description = 'Product Checker Saved Filter'
    _order = 'is_default desc, name asc'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        default=lambda self: self.env.user, ondelete='cascade', index=True,
    )
    domain = fields.Text(
        string='Domain',
        default='[]',
        help='Domain string from the Custom Filter dialog (Domain Selector).',
    )
    query = fields.Char(
        string='Search Query',
        default='',
        help='Text typed in the drawer search box when this filter was saved.',
    )
    is_default = fields.Boolean(
        string='Default',
        default=False,
        help='Auto-apply this filter when the drawer is opened. Only one '
             'default per user is allowed.',
    )

    _sql_constraints = [
        ('unique_user_name', 'unique(user_id, name)',
         'You already have a saved filter with this name.'),
    ]

    @api.model
    def _ensure_single_default(self, user_id, keep_id=None):
        """Ensure at most one default filter per user."""
        domain = [('user_id', '=', user_id), ('is_default', '=', True)]
        if keep_id:
            domain.append(('id', '!=', keep_id))
        others = self.search(domain)
        if others:
            others.write({'is_default': False})

    # ============================================================
    # RPC methods called from the Product Checker client action
    # ============================================================

    @api.model
    def get_saved_filters(self):
        """Return the current user's saved filters, sorted by default-first."""
        records = self.search([('user_id', '=', self.env.user.id)])
        return [{
            'id': r.id,
            'name': r.name,
            'domain': r.domain or '[]',
            'query': r.query or '',
            'is_default': r.is_default,
        } for r in records]

    @api.model
    def save_current_filter(self, name, domain, query='', is_default=False):
        """
        Create or update a saved filter for the current user.

        If a filter with the same name already exists for this user, it is
        updated (upsert-by-name). If `is_default` is True, any other default
        for this user is cleared first.

        Returns:
            dict: {'success': bool, 'filter': {...}, 'error': str}
        """
        name = (name or '').strip()
        if not name:
            return {'success': False, 'error': _('Name is required')}

        vals = {
            'name': name,
            'user_id': self.env.user.id,
            'domain': domain or '[]',
            'query': query or '',
            'is_default': bool(is_default),
        }

        try:
            existing = self.search([
                ('user_id', '=', self.env.user.id),
                ('name', '=', name),
            ], limit=1)
            if existing:
                existing.write(vals)
                record = existing
            else:
                record = self.create(vals)

            if record.is_default:
                self._ensure_single_default(self.env.user.id, keep_id=record.id)
        except Exception as e:
            return {'success': False, 'error': str(e)}

        return {
            'success': True,
            'filter': {
                'id': record.id,
                'name': record.name,
                'domain': record.domain or '[]',
                'query': record.query or '',
                'is_default': record.is_default,
            },
        }

    @api.model
    def delete_saved_filter(self, filter_id):
        """Delete a saved filter. Silently ignores missing / foreign records."""
        record = self.search([
            ('id', '=', int(filter_id)),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if record:
            record.unlink()
        return {'success': True}

    @api.model
    def set_default_filter(self, filter_id):
        """Set a filter as the default (or clear default if filter_id is falsy)."""
        if not filter_id:
            self._ensure_single_default(self.env.user.id)
            return {'success': True}

        record = self.search([
            ('id', '=', int(filter_id)),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if not record:
            return {'success': False, 'error': _('Filter not found')}

        self._ensure_single_default(self.env.user.id, keep_id=record.id)
        record.write({'is_default': True})
        return {'success': True}
