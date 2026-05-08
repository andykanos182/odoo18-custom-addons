from odoo import fields, models


class KitchenPushSubscription(models.Model):
    """Stores a Web Push subscription from a staff device.

    One row per (device, browser). The same phone can have multiple rows if the
    user reinstalls the PWA — old rows become inactive when push delivery fails.
    """
    _name = 'kitchen.push.subscription'
    _description = 'Kitchen Push Subscription'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Optional — link to an HR employee for reporting',
    )
    device_name = fields.Char(
        string='Device Name',
        default='Kitchen Device',
    )

    endpoint = fields.Char(
        string='Endpoint',
        required=True,
        help='Push service URL provided by the browser',
    )
    p256dh = fields.Char(
        string='P256DH Key',
        required=True,
        help='Public key for message encryption',
    )
    auth = fields.Char(
        string='Auth Secret',
        required=True,
        help='Authentication secret for the subscription',
    )

    is_active = fields.Boolean(string='Active', default=True)
    last_notif_at = fields.Datetime(string='Last Notification At')
    fail_count = fields.Integer(string='Consecutive Failures', default=0)

    _sql_constraints = [
        (
            'endpoint_unique',
            'unique(endpoint)',
            'A subscription with this endpoint already exists.',
        ),
    ]
