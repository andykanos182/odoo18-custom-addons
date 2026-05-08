# -*- coding: utf-8 -*-
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, route
import json
import logging

_logger = logging.getLogger(__name__)


class WebsiteSaleExtended(WebsiteSale):

    def _prepare_address_form_values(
        self, order_sudo, partner_sudo, address_type,
        use_delivery_as_billing, callback='', **kwargs
    ):
        """Override untuk inject Google Maps API Key ke template checkout."""
        values = super()._prepare_address_form_values(
            order_sudo, partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback, **kwargs
        )

        IrConfig = request.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('base_geolocalize.google_map_api_key', '')
        values['google_maps_api_key'] = api_key

        return values

    @route(
        '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def shop_address_submit(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
        required_fields=None, **form_data
    ):
        _logger.info("=== [Andyka] shop_address_submit override aktif ===")

        gmaps_link = form_data.get('gmaps_link')
        partner_lat = form_data.get('partner_latitude')
        partner_lng = form_data.get('partner_longitude')

        response = super().shop_address_submit(
            partner_id=partner_id,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            required_fields=required_fields,
            **form_data
        )

        try:
            response_data = json.loads(response.get_data().decode('utf8'))

            if 'redirectUrl' in response_data:
                order_sudo = request.website.sale_get_order()

                if address_type == 'delivery':
                    partner_to_update = order_sudo.partner_shipping_id
                else:
                    partner_to_update = order_sudo.partner_invoice_id

                if partner_to_update:
                    write_vals = {}

                    if gmaps_link:
                        write_vals['gmaps_link'] = gmaps_link

                    if partner_lat and partner_lng:
                        try:
                            lat = float(partner_lat)
                            lng = float(partner_lng)
                            if lat != 0 or lng != 0:
                                write_vals['partner_latitude'] = lat
                                write_vals['partner_longitude'] = lng
                        except (ValueError, TypeError):
                            _logger.warning("[Andyka] Format koordinat tidak valid: %s, %s", partner_lat, partner_lng)

                    if write_vals:
                        partner_to_update.sudo().write(write_vals)
                        _logger.info("[Andyka] Data tersimpan untuk Partner ID %s: %s", partner_to_update.id, write_vals)

        except Exception as e:
            _logger.error("[Andyka] Gagal memproses response atau menyimpan data: %s", e)

        return response
