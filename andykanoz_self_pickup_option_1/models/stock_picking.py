# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _is_self_pickup_order(self):
        """Cek apakah picking ini terkait dengan order Self Pickup."""
        self.ensure_one()
        # Cek dari sale order yang terkait
        sale_order = self.sale_id
        if sale_order and sale_order.carrier_id:
            carrier_name = sale_order.carrier_id.name or ''
            if 'ambil sendiri' in carrier_name.lower() or 'self pickup' in carrier_name.lower():
                return True
        return False

    def _send_confirmation_email(self):
        """
        Override: Jika Self Pickup, kirim email template Self Pickup.
        Jika bukan, kirim email template standar (delivery).
        """
        for picking in self:
            if picking._is_self_pickup_order():
                # Kirim email Self Pickup
                template = self.env.ref(
                    'andykanoz_self_pickup_option_1.mail_template_self_pickup_ready',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(picking.id, force_send=True)
                    _logger.info(
                        "[Self Pickup] Email 'Pesanan Siap Diambil' terkirim untuk %s",
                        picking.name
                    )
            else:
                # Kirim email delivery standar
                super(StockPicking, picking)._send_confirmation_email()

    def button_validate(self):
        """
        Override button_validate: setelah validate, kirim email yang sesuai.
        """
        res = super().button_validate()

        for picking in self:
            if picking.state == 'done' and picking.picking_type_id.code == 'outgoing':
                if picking._is_self_pickup_order():
                    # Kirim email Self Pickup
                    template = self.env.ref(
                        'andykanoz_self_pickup_option_1.mail_template_self_pickup_ready',
                        raise_if_not_found=False
                    )
                    if template:
                        template.send_mail(picking.id, force_send=True)
                        _logger.info(
                            "[Self Pickup] Email 'Pesanan Siap Diambil' terkirim untuk %s (SO: %s)",
                            picking.name,
                            picking.sale_id.name if picking.sale_id else 'N/A'
                        )

        return res
