# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

MAX_BATCH = 50


class AndykanozBatchEditWizard(models.TransientModel):
    _name = 'andykanoz.batch.edit.wizard'
    _description = 'Auto White BG Batch Wizard'

    product_ids = fields.Many2many(
        'product.template', string='Products with Image',
    )
    total_selected = fields.Integer(string='Selected', readonly=True)
    total_with_image = fields.Integer(string='With Image', readonly=True)
    total_skipped = fields.Integer(
        string='Skipped (no image)',
        compute='_compute_skipped', store=False,
    )
    daily_quota_limit = fields.Integer(string='Daily Quota Limit', readonly=True)
    daily_quota_used = fields.Integer(string='Used Today', readonly=True)
    daily_quota_remaining = fields.Integer(
        string='Remaining', compute='_compute_quota_remaining',
    )
    # Batch-level override options (user can select presets before starting)
    preset = fields.Selection([
        ('default', 'Default'),
        ('refine_white', 'Refine — White background'),
        ('transparent', 'Transparent — PNG with alpha'),
        ('remove_hands', 'Remove hands / occlusions'),
        ('custom', 'Custom prompt'),
    ], string='Preset', default='default')
    custom_prompt = fields.Text(string='Custom Prompt')
    output_format = fields.Selection([('jpeg', 'JPEG (white background)'), ('png', 'PNG (transparent)')], string='Output Format', default='jpeg')
    refine_edges = fields.Boolean(string='Refine edges', default=False)
    preserve_shadows = fields.Boolean(string='Preserve shadows', default=True)
    max_dimension = fields.Integer(string='Max dimension (px)', default=0)
    use_professional_preset = fields.Boolean(string='Use Professional Preset', default=False)
    has_active_job = fields.Boolean(string='Active Job Exists', readonly=True)
    blocking_reason = fields.Char(string='Blocking Reason', readonly=True)
    can_start = fields.Boolean(string='Can Start', compute='_compute_can_start')

    @api.depends('total_selected', 'total_with_image')
    def _compute_skipped(self):
        for w in self:
            w.total_skipped = max(w.total_selected - w.total_with_image, 0)

    @api.depends('daily_quota_limit', 'daily_quota_used')
    def _compute_quota_remaining(self):
        for w in self:
            w.daily_quota_remaining = max(w.daily_quota_limit - w.daily_quota_used, 0)

    @api.depends('blocking_reason')
    def _compute_can_start(self):
        for w in self:
            w.can_start = not w.blocking_reason

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        active_ids = ctx.get('active_ids') or []
        active_model = ctx.get('active_model') or 'product.template'

        if active_model == 'product.product':
            variants = self.env['product.product'].browse(active_ids)
            templates = variants.product_tmpl_id
        else:
            templates = self.env['product.template'].browse(active_ids)
        templates = templates.exists()

        with_image = templates.filtered(lambda t: t.image_1920)

        self.env['product.template']._ensure_quota_fresh()
        ICP = self.env['ir.config_parameter'].sudo()
        limit = int(ICP.get_param('andykanoz_gemini_integration_auto_edit.daily_quota_limit', '100') or '100')
        used = int(ICP.get_param('andykanoz_gemini_integration_auto_edit.quota_used', '0') or '0')
        remaining = max(limit - used, 0)

        # Load default preset/options from system config unless overridden by context
        cfg_preset = ICP.get_param('andykanoz_gemini_integration_auto_edit.preset', 'default') or 'default'
        cfg_custom_prompt = ICP.get_param('andykanoz_gemini_integration_auto_edit.custom_prompt', '') or ''
        cfg_output_format = ICP.get_param('andykanoz_gemini_integration_auto_edit.output_format', 'jpeg') or 'jpeg'
        cfg_refine = str(ICP.get_param('andykanoz_gemini_integration_auto_edit.refine_edges', 'False')).lower() in ('1', 'true', 'yes')
        cfg_preserve = str(ICP.get_param('andykanoz_gemini_integration_auto_edit.preserve_shadows', 'True')).lower() in ('1', 'true', 'yes')
        try:
            cfg_max_dim = int(ICP.get_param('andykanoz_gemini_integration_auto_edit.max_dimension', '0') or '0')
        except Exception:
            cfg_max_dim = 0

        active_job = self.env['andykanoz.batch.edit.job']._get_active_job_for_user()

        reason = ''
        if active_job:
            reason = _("You already have a batch in progress: %s. Wait for it to finish or cancel it first.") % active_job.name
        elif not with_image:
            reason = _("None of the selected products have an image to process.")
        elif len(with_image) > MAX_BATCH:
            reason = _("Batch is limited to %d products. You selected %d (with image).") % (MAX_BATCH, len(with_image))
        elif len(with_image) > remaining:
            reason = _("Daily quota only has %d remaining, but %d would be needed.") % (remaining, len(with_image))

        # If opened via 'Auto Pro Edit (Bulk)' action, prefill professional preset
        if ctx.get('andykanoz_professional_preset'):
            preset_val = 'remove_hands'
            custom_prompt_val = ''
            output_format_val = 'jpeg'
            refine_val = True
            preserve_val = True
            max_dim_val = 0
        else:
            preset_val = cfg_preset
            custom_prompt_val = cfg_custom_prompt
            output_format_val = cfg_output_format
            refine_val = cfg_refine
            preserve_val = cfg_preserve
            max_dim_val = cfg_max_dim

        res.update({
            'product_ids': [(6, 0, with_image.ids)],
            'total_selected': len(templates),
            'total_with_image': len(with_image),
            'daily_quota_limit': limit,
            'daily_quota_used': used,
            'has_active_job': bool(active_job),
            'blocking_reason': reason,
            'use_professional_preset': bool(ctx.get('andykanoz_professional_preset', False)),
            'preset': preset_val,
            'custom_prompt': custom_prompt_val,
            'output_format': output_format_val,
            'refine_edges': refine_val,
            'preserve_shadows': preserve_val,
            'max_dimension': max_dim_val,
        })
        return res

    def action_start(self):
        self.ensure_one()
        if self.blocking_reason:
            raise UserError(self.blocking_reason)
        if not self.product_ids:
            raise UserError(_("No products to process."))

        Job = self.env['andykanoz.batch.edit.job']
        active = Job._get_active_job_for_user()
        if active:
            raise UserError(_("You already have a batch job in progress: %s") % active.name)

        line_vals = [
            (0, 0, {'product_tmpl_id': p.id, 'sequence': idx * 10})
            for idx, p in enumerate(self.product_ids)
        ]
        job_vals = {'line_ids': line_vals}
        # Always include wizard-chosen overrides (may be defaults)
        job_vals.update({
            'preset': (self.preset or 'default'),
            'custom_prompt': (self.custom_prompt or False),
            'output_format': (self.output_format or 'jpeg'),
            'refine_edges': bool(self.refine_edges),
            'preserve_shadows': bool(self.preserve_shadows),
            'max_dimension': int(self.max_dimension or 0),
        })
        job = Job.create(job_vals)
        job.action_start()

        return {
            'type': 'ir.actions.client',
            'tag': 'andykanoz_gemini_integration_auto_edit.open_progress_dialog',
            'params': {'job_id': job.id},
        }
