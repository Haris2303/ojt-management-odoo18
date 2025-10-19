# -*- coding: utf-8 -*-
import base64
import io
import logging

try:
    import qrcode
except ImportError:
    qrcode = None
    logging.getLogger(__name__).warning("The 'qrcode' library is not installed. QR code generation will be disabled.")

from odoo.exceptions import ValidationError
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

    title = fields.Char(string='Title', related='event_id.name', readonly=False)
    date_start = fields.Datetime(string='Date Start', related='event_id.date_begin', readonly=False)
    date_end = fields.Datetime(string='Date End', related='event_id.date_end', readonly=False)
    instructor_id = fields.Many2one('res.partner', string='Instructor / Speaker')
    notes = fields.Text(string='Notes')
    qr_code_image = fields.Binary("QR Code", compute='_compute_qr_code')

    participant_count = fields.Integer(compute='_compute_related_counts')
    attendance_count = fields.Integer(compute='_compute_related_counts')
    assignment_count = fields.Integer(compute='_compute_related_counts')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            # Pastikan date_start tidak di masa lalu
            if record.date_start and record.date_start < fields.Datetime.now():
                raise ValidationError("Tanggal mulai (Date Start) tidak boleh di masa lalu!")

            # Pastikan date_end tidak sebelum date_start
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("Tanggal berakhir (Date End) tidak boleh sebelum tanggal mulai (Date Start)!")


    @api.depends('batch_id.participant_ids', 'event_id')
    def _compute_related_counts(self):
        for rec in self:
            rec.participant_count = rec.batch_id.participant_count
            rec.attendance_count = self.env['ojt.attendance'].search_count([('event_link_id', '=', rec.id)])
            rec.assignment_count = self.env['ojt.assignment'].search_count([('event_link_id', '=', rec.id)])

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

    def action_view_participants(self):
        self.ensure_one()
        return {
            'name': 'Participants', 'type': 'ir.actions.act_window', 'res_model': 'ojt.participant',
            'view_mode': 'list,form', 'domain': [('id', 'in', self.batch_id.participant_ids.ids)],
        }

    def action_view_attendance_log(self):
        self.ensure_one()
        return {
            'name': 'Attendance Log', 'type': 'ir.actions.act_window', 'res_model': 'ojt.attendance',
            'view_mode': 'list,form', 'domain': [('event_link_id', '=', self.id)],
        }