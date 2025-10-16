# -*- coding: utf-8 -*-
import base64
import io
import logging

try:
    import qrcode
except ImportError:
    qrcode = None
    logging.getLogger(__name__).warning("The 'qrcode' library is not installed. QR code generation will be disabled.")

from odoo import models, fields, api

class OjtEventLink(models.Model):
    _name = 'ojt.event.link'
    _description = 'OJT Batch to Event Link'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, ondelete='cascade')
    event_id = fields.Many2one('event.event', string='Event/Session', required=True)
    
    is_mandatory = fields.Boolean(
        string='Is Mandatory?', default=True, tracking=True,
        help="Check if attendance for this session is mandatory for the certificate.")
    weight = fields.Float(
        string='Session Weight', default=1.0, tracking=True,
        help="Weight of this session for progress calculation.")
    
    online_meeting_url = fields.Char(
        string='Online Meeting URL',
        help="Override/shortcut for the meeting link. If empty, the link from the event will be used.")
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

    @api.model
    def create(self, vals):
        """ On creation, send a notification email to all participants of the batch. """
        new_event_link = super(OjtEventLink, self).create(vals)

        template = self.env.ref('solvera_ojt_core.mail_template_new_ojt_agenda', raise_if_not_found=False)
        
        if template and new_event_link.batch_id.participant_ids:
            for participant in new_event_link.batch_id.participant_ids:
                if participant.partner_id.email:
                    email_context = {
                        'participant_name_placeholder': participant.partner_id.name,
                        'participant_email_placeholder': participant.partner_id.email,
                    }
                    template.with_context(**email_context).send_mail(new_event_link.id, force_send=True)

        return new_event_link