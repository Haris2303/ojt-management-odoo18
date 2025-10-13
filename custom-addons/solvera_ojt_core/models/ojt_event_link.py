# -*- coding: utf-8 -*-
import base64
import io
try:
    import qrcode
except ImportError:
    qrcode = None

from odoo import models, fields

class OjtEventLink(models.Model):
    _name = 'ojt.event.link'
    _description = 'OJT Batch to Event Link'

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, ondelete='cascade')
    event_id = fields.Many2one('event.event', string='Event/Session', required=True)
    
    is_mandatory = fields.Boolean(string='Is Mandatory?', default=True, help="Check if attendance for this session is mandatory for the certificate.")
    weight = fields.Float(string='Session Weight', default=1.0, help="Weight of this session for progress calculation.")
    
    # This field allows overriding the meeting link from the main event, for specific batches.
    online_meeting_url = fields.Char(string='Online Meeting URL', help="Override/shortcut for the meeting link. If empty, the link from the event will be used.")
    notes = fields.Text(string='Notes')

    qr_code_image = fields.Binary("QR Code", compute='_compute_qr_code')

    def _compute_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if qrcode and rec.id:
                qr_url = f'{base_url}/ojt/attend/{rec.id}'
                img = qrcode.make(qr_url)
                temp = io.BytesIO()
                img.save(temp, format="PNG")
                rec.qr_code_image = base64.b64encode(temp.getvalue())
            else:
                rec.qr_code_image = False