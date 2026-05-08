# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class QuickPurchaseSession(models.Model):
    """Stores Quick Purchase session state per user.
    
    Supports multiple tabs/drafts per user.
    """
    _name = "quick.purchase.session"
    _description = "Quick Purchase Session"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=True,
        ondelete="cascade",
    )
    session_id = fields.Char(string="Session ID (Client)", required=True, index=True)
    name = fields.Char(string="Session Name", default="New Draft")
    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
    )
    partner_name = fields.Char(string="Vendor Name")
    lines_json = fields.Text(
        string="Lines (JSON)",
        default="[]",
        help="JSON-serialized list of line dicts.",
    )
    
    _sql_constraints = [
        (
            "user_session_unique",
            "UNIQUE(user_id, session_id)",
            "Each user can only have one active session per ID.",
        ),
    ]

    @api.model
    def sync_sessions(self, sessions_data, active_session_id):
        """Sync sessions from client to server and return the latest state."""
        user_id = self.env.uid
        
        # Get existing sessions for this user
        existing_records = self.search([("user_id", "=", user_id)])
        existing_map = {r.session_id: r for r in existing_records}
        
        # Determine which sessions are still active from the client
        client_session_ids = [s.get("id") for s in sessions_data if s.get("id")]
        
        # 1. Delete sessions that are no longer in the client's payload
        to_delete = existing_records.filtered(lambda r: r.session_id not in client_session_ids)
        if to_delete:
            to_delete.unlink()
            
        # 2. Update or Create sessions
        for s_data in sessions_data:
            s_id = s_data.get("id")
            if not s_id:
                continue
                
            vals = {
                "name": s_data.get("name") or "New Draft",
                "partner_id": int(s_data.get("partnerId")) if s_data.get("partnerId") else False,
                "partner_name": s_data.get("partnerName") or "",
                "lines_json": json.dumps(s_data.get("lines") or []),
            }
            
            if s_id in existing_map:
                existing_map[s_id].write(vals)
            else:
                vals["user_id"] = user_id
                vals["session_id"] = s_id
                self.create(vals)
                
        return True

    @api.model
    def load_sessions(self):
        """Load all sessions for the current user."""
        records = self.search([("user_id", "=", self.env.uid)])
        result = []
        for r in records:
            try:
                lines = json.loads(r.lines_json or "[]")
            except (json.JSONDecodeError, TypeError):
                lines = []
                
            result.append({
                "id": r.session_id,
                "name": r.name,
                "partnerId": r.partner_id.id if r.partner_id else None,
                "partnerName": r.partner_name or "",
                "lines": lines,
            })
        return result
        
    @api.model
    def clear_session(self, session_id):
        """Delete a specific session."""
        session = self.search([("user_id", "=", self.env.uid), ("session_id", "=", session_id)], limit=1)
        if session:
            session.unlink()
        return True