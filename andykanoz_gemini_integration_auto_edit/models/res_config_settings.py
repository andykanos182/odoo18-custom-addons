# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_edit_gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter='andykanoz_gemini_integration_auto_edit.gemini_api_key',
    )
    auto_edit_daily_quota_limit = fields.Integer(
        string="Daily Quota Limit",
        config_parameter='andykanoz_gemini_integration_auto_edit.daily_quota_limit',
        default=100,
        help="Maximum number of Gemini Auto Edit calls allowed per day.",
    )
    auto_edit_preset = fields.Selection(
        [
            ('default', 'Default (current)'),
            ('refine_white', 'Refine — White background (higher quality)'),
            ('transparent', 'Transparent — PNG with alpha'),
            ('remove_hands', 'Remove hands / occlusions'),
            ('custom', 'Custom prompt'),
        ],
        string="Auto Edit Preset",
        config_parameter='andykanoz_gemini_integration_auto_edit.preset',
        default='default',
        help="Choose a prompt preset for Auto Edit. 'Default' preserves current behaviour.",
    )
    auto_edit_custom_prompt = fields.Char(
        string="Custom Gemini Prompt",
        config_parameter='andykanoz_gemini_integration_auto_edit.custom_prompt',
        help="If preset is 'Custom', this prompt will be sent to Gemini instead of built-in prompts.",
    )
    auto_edit_output_format = fields.Selection(
        [('jpeg', 'JPEG (white background)'), ('png', 'PNG (transparent/background)')],
        string='Output Format',
        config_parameter='andykanoz_gemini_integration_auto_edit.output_format',
        default='jpeg',
        help='Desired output image format.',
    )
    auto_edit_refine_edges = fields.Boolean(
        string='Refine edges',
        config_parameter='andykanoz_gemini_integration_auto_edit.refine_edges',
        default=False,
        help='Attempt to refine cutout edges to avoid halos.',
    )
    auto_edit_preserve_shadows = fields.Boolean(
        string='Preserve natural shadows',
        config_parameter='andykanoz_gemini_integration_auto_edit.preserve_shadows',
        default=True,
        help='Preserve subtle natural shadows for a realistic look.',
    )
    auto_edit_max_dimension = fields.Integer(
        string='Max dimension (px)',
        config_parameter='andykanoz_gemini_integration_auto_edit.max_dimension',
        default=0,
        help='If >0, images may be resized before sending to reduce API cost (not applied in Phase 1).',
    )
