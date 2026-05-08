# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ACTIVE_STATES = ('draft', 'running')
TERMINAL_STATES = ('done', 'cancelled', 'failed')

CRON_XMLID = 'andykanoz_gemini_integration_auto_edit.ir_cron_process_batch_jobs'
BUS_CHANNEL = 'andykanoz_gemini_integration_auto_edit.job_update'


class AndykanozBatchEditJob(models.Model):
    _name = 'andykanoz.batch.edit.job'
    _description = 'Auto Edit Batch Job'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        default=lambda self: self.env.user, index=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('running', 'Running'),
         ('done', 'Done'),
         ('cancelled', 'Cancelled'),
         ('failed', 'Failed')],
        string='Status', default='draft', required=True, index=True,
    )
    line_ids = fields.One2many(
        'andykanoz.batch.edit.job.line', 'job_id', string='Lines',
    )
    total_count = fields.Integer(string='Total', compute='_compute_counters', store=True)
    processed_count = fields.Integer(string='Processed', default=0)
    failed_count = fields.Integer(string='Failed', default=0)
    current_line_id = fields.Many2one(
        'andykanoz.batch.edit.job.line', string='Currently Processing',
    )
    created_at = fields.Datetime(string='Created At', default=fields.Datetime.now)
    completed_at = fields.Datetime(string='Completed At')
    # Optional overrides for batch processing (if set, they are passed to _gemini_remove_white_bg)
    preset = fields.Selection(
        [
            ('default', 'Default'),
            ('refine_white', 'Refine — White'),
            ('transparent', 'Transparent — PNG'),
            ('remove_hands', 'Remove hands / occlusions'),
            ('custom', 'Custom'),
        ],
        string='Preset',
        default='default',
    )
    custom_prompt = fields.Text(string='Custom Prompt')
    output_format = fields.Selection([('jpeg', 'JPEG'), ('png', 'PNG')], string='Output Format')
    refine_edges = fields.Boolean(string='Refine edges')
    preserve_shadows = fields.Boolean(string='Preserve shadows')
    max_dimension = fields.Integer(string='Max dimension (px)')

    @api.depends('line_ids')
    def _compute_counters(self):
        for job in self:
            job.total_count = len(job.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'andykanoz.batch.edit.job'
                ) or _('Batch Edit')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_active_job_for_user(self, user_id=None):
        user_id = user_id or self.env.uid
        return self.search([
            ('user_id', '=', user_id),
            ('state', 'in', list(ACTIVE_STATES)),
        ], limit=1)

    def _job_payload(self):
        self.ensure_one()
        current_name = ''
        if self.current_line_id:
            current_name = self.current_line_id.product_tmpl_id.display_name or ''
        return {
            'job_id': self.id,
            'name': self.name,
            'state': self.state,
            'total': self.total_count,
            'processed': self.processed_count,
            'failed': self.failed_count,
            'current_product_name': current_name,
            'preset': self.preset,
            'processed_by': self.user_id.id,
        }

    def _notify_progress(self):
        for job in self:
            self.env['bus.bus']._sendone(
                job.user_id.partner_id,
                BUS_CHANNEL,
                job._job_payload(),
            )

    # ------------------------------------------------------------------
    # User actions
    # ------------------------------------------------------------------
    def action_start(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("This job is not in draft state."))
        existing = self.search([
            ('user_id', '=', self.user_id.id),
            ('state', '=', 'running'),
            ('id', '!=', self.id),
        ], limit=1)
        if existing:
            raise UserError(_("You already have a running batch job: %s") % existing.name)
        self.env['product.template']._ensure_quota_fresh()
        self.state = 'running'
        self._notify_progress()
        try:
            self.env.ref(CRON_XMLID)._trigger()
        except Exception:
            _logger.exception("Failed to trigger batch edit cron")
        return True

    def action_cancel(self):
        for job in self:
            if job.state in TERMINAL_STATES:
                continue
            job.state = 'cancelled'
            job.completed_at = fields.Datetime.now()
            job._notify_progress()
        return True

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def _finalize(self):
        self.ensure_one()
        if self.failed_count and not self.processed_count:
            self.state = 'failed'
        else:
            self.state = 'done'
        self.completed_at = fields.Datetime.now()
        self.current_line_id = False
        self._notify_progress()

    def _process_lines(self):
        self.ensure_one()
        while True:
            self.env.cr.commit()
            self.invalidate_recordset(['state'])
            if self.state != 'running':
                break

            line = self.line_ids.filtered(lambda l: l.state == 'pending')[:1]
            if not line:
                self._finalize()
                self.env.cr.commit()
                break

            self.current_line_id = line.id
            self._notify_progress()
            self.env.cr.commit()

            try:
                line._process()
                self.processed_count += 1
            except Exception as e:
                _logger.exception("Batch edit line %s failed", line.id)
                line.write({
                    'state': 'failed',
                    'error_message': (str(e) or '')[:500],
                    'processed_at': fields.Datetime.now(),
                })
                self.failed_count += 1

            self._notify_progress()
            self.env.cr.commit()

    @api.model
    def _cron_process_jobs(self):
        jobs = self.search([('state', '=', 'running')])
        for job in jobs:
            try:
                job._process_lines()
            except Exception:
                _logger.exception("Batch edit job %s crashed", job.id)
                job.write({'state': 'failed', 'completed_at': fields.Datetime.now()})
                job._notify_progress()
                self.env.cr.commit()


class AndykanozBatchEditJobLine(models.Model):
    _name = 'andykanoz.batch.edit.job.line'
    _description = 'Auto Edit Batch Job Line'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'andykanoz.batch.edit.job', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True, ondelete='cascade',
    )
    state = fields.Selection(
        [('pending', 'Pending'),
         ('done', 'Done'),
         ('failed', 'Failed')],
        default='pending', required=True, index=True,
    )
    error_message = fields.Text(string='Error')
    processed_at = fields.Datetime(string='Processed At')

    def _process(self):
        self.ensure_one()
        product = self.product_tmpl_id
        if not product.image_1920:
            raise UserError(_("Product has no image."))
        # Pass job-level overrides to the API call when present
        job = self.job_id
        new_b64 = product._gemini_remove_white_bg(
            product.image_1920.decode('ascii'),
            preset_override=(job.preset or None),
            custom_prompt_override=(job.custom_prompt or None),
            output_format_override=(job.output_format or None),
            refine_edges_override=(job.refine_edges if job.refine_edges is not None else None),
            preserve_shadows_override=(job.preserve_shadows if job.preserve_shadows is not None else None),
            max_dimension_override=(job.max_dimension if job.max_dimension else None),
        )
        product.write({'image_1920': new_b64})
        self.write({
            'state': 'done',
            'processed_at': fields.Datetime.now(),
        })
