# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalExtended(CustomerPortal):

    def _get_mandatory_fields(self):
        fields = super()._get_mandatory_fields()
        return fields

    def _get_optional_fields(self):
        fields = super()._get_optional_fields()
        fields.extend(['gmaps_link', 'partner_latitude', 'partner_longitude'])
        return fields

    def on_account_update(self, values, partner):
        """
        Override untuk konversi partner_latitude & partner_longitude
        dari string ke float SEBELUM partner.write() dipanggil.
        Field TIDAK di-pop dari values, supaya ikut tersimpan bersama
        field alamat lain (mencegah reset oleh base_geolocalize).
        """
        super().on_account_update(values, partner)

        # Konversi string ke float agar partner.write() tidak error
        for field in ['partner_latitude', 'partner_longitude']:
            if field in values:
                try:
                    val = float(values[field])
                    values[field] = val
                except (ValueError, TypeError):
                    values.pop(field, None)

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        response = super().account(redirect=redirect, **post)

        if hasattr(response, 'qcontext'):
            IrConfig = request.env['ir.config_parameter'].sudo()
            api_key = IrConfig.get_param('base_geolocalize.google_map_api_key', '')
            response.qcontext['google_maps_api_key'] = api_key

        return response
