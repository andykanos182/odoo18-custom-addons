# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AndykanozAutoEditController(http.Controller):

    @http.route('/andykanoz_gemini_integration_auto_edit/get_active_job', type='json', auth='user')
    def get_active_job(self, **kwargs):
        job = request.env['andykanoz.batch.edit.job']._get_active_job_for_user()
        if not job:
            # Return latest terminal job from today (so dialog can flash final state)
            return None
        return job._job_payload()

    @http.route('/andykanoz_gemini_integration_auto_edit/cancel_job', type='json', auth='user')
    def cancel_job(self, job_id=None, **kwargs):
        if not job_id:
            return {'ok': False, 'error': 'missing job_id'}
        job = request.env['andykanoz.batch.edit.job'].browse(int(job_id))
        if not job.exists():
            return {'ok': False, 'error': 'not found'}
        if job.user_id.id != request.env.uid and not request.env.user.has_group('base.group_system'):
            return {'ok': False, 'error': 'forbidden'}
        job.action_cancel()
        return {'ok': True}
