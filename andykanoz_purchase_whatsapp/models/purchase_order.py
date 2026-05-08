# -*- coding: utf-8 -*-
import re
from urllib.parse import quote_plus
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _sanitize_phone(self, phone):
        if not phone:
            return None
        # remove all non-digit characters
        number = re.sub(r'\D', '', phone)
        return number

    def _get_order_type(self):
        return "RFQ" if self.state == 'draft' else "PO"

    def _build_whatsapp_message(self):
        self.ensure_one()
        parts = []
        parts.append(f"{self._get_order_type()} {self.name or ''}")
        parts.append(f"Penyedia: {self.partner_id.name or ''}")
        if self.date_order:
            parts.append(f"Tanggal: {str(self.date_order)}")
        parts.append("")
        parts.append("Daftar Produk:")
        for line in self.order_line:
            prod = line.product_id.display_name
            qty = line.product_qty
            uom = line.product_uom.name or ''
            price = line.price_unit
            subtotal = line.price_subtotal
            parts.append(f"- {prod} x{qty} {uom} @ {price} => {subtotal}")
        parts.append("")
        parts.append(f"Total: {self.amount_total} {getattr(self.currency_id, 'symbol', '') or getattr(self.currency_id, 'name', '')}")
        text = "\n".join(parts)
        # If message too long for URL, fallback to short message with link to record
        if len(text) > 1500:
            base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
            order_url = f"{base}/web#id={self.id}&model=purchase.order&view_type=form"
            text = f"{self._get_order_type()} {self.name}\nPenyedia: {self.partner_id.name}\nDaftar produk terlalu panjang, lihat detail: {order_url}"
        return text

    def action_send_whatsapp(self):
        self.ensure_one()
        phone = self.partner_id.phone or self.partner_id.mobile
        phone = self._sanitize_phone(phone)
        if not phone:
            raise UserError(_("Partner tidak memiliki nomor telepon. Tambahkan nomor dalam format internasional (contoh: 628123456789)."))
        message = self._build_whatsapp_message()
        url_text = quote_plus(message)
        url = f"https://api.whatsapp.com/send?phone={phone}&text={url_text}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
