# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class DokuPortal(CustomerPortal):

    def _doku_auto_cancel_expired(self, txs):
        """Lazy auto-cancellation for expired DOKU transactions."""
        now = fields.Datetime.now()
        for tx in txs:
            if tx.state in ('draft', 'pending') and tx.doku_expired_at and tx.doku_expired_at < now:
                try:
                    # Sync status to ensure it's not actually paid
                    tx._doku_sync_status()
                    if tx.state in ('draft', 'pending'):
                        tx._set_canceled(state_message=_("Otomatis dibatalkan karena batas waktu pembayaran habis."))
                except Exception:
                    pass

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        
        if 'doku_pending_count' in counters:
            domain = self._doku_prepare_pending_domain(partner)
            # Fetch and lazily cancel expired before counting
            txs = request.env['payment.transaction'].sudo().search(domain)
            self._doku_auto_cancel_expired(txs)
            
            # Recalculate count after lazy cancel
            values['doku_pending_count'] = request.env['payment.transaction'].sudo().search_count(domain)
            
        return values

    def _doku_prepare_pending_domain(self, partner):
        return [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
            ('provider_code', '=', 'doku'),
            ('state', 'in', ['draft', 'pending']),
            ('doku_payment_url', '!=', False)
        ]

    @http.route(['/my/doku/pending', '/my/doku/pending/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_doku_pending(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PaymentTx = request.env['payment.transaction']

        domain = self._doku_prepare_pending_domain(partner)

        searchbar_sortings = {
            'date': {'label': _('Tanggal'), 'order': 'create_date desc'},
            'amount': {'label': _('Nominal'), 'order': 'amount desc'},
        }
        
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        # count for pager
        tx_count = PaymentTx.sudo().search_count(domain)
        
        # pager
        pager = portal_pager(
            url="/my/doku/pending",
            url_args={'sortby': sortby},
            total=tx_count,
            page=page,
            step=self._items_per_page
        )
        
        # content
        transactions = PaymentTx.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        
        # We don't auto cancel here because the home values check already did it for all txs of the user,
        # but just to be safe:
        self._doku_auto_cancel_expired(transactions)
        
        # filter out the ones we just cancelled so they don't show up in the table
        transactions = transactions.filtered(lambda t: t.state in ('draft', 'pending'))
        
        values.update({
            'date': sortby == 'date',
            'transactions': transactions,
            'page_name': 'doku_pending',
            'pager': pager,
            'default_url': '/my/doku/pending',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("andykanoz_doku_payment_geteway.portal_my_doku_pending", values)
