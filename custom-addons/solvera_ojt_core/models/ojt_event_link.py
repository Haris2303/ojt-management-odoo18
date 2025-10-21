# -*- coding: utf-8 -*-
import uuid
import base64
import io

try:
    import qrcode
except ImportError:
    qrcode = None

from odoo.exceptions import ValidationError
from odoo import models, fields, api

class OjtEventLink(models.Model):
    _name = 'ojt.event.link'
    _description = 'OJT Batch to Event Link'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    batch_id = fields.Many2one(
        'ojt.batch', 
        string='OJT Batch', 
        required=True, 
        ondelete='cascade',
        domain="[('state', '=', 'ongoing')]"
    )
    event_id = fields.Many2one(
        'event.event', 
        string='Event/Session', 
        required=True, 
        domain="[('date_begin', '>=', context_today().strftime('%Y-%m-%d'))]"
    )
    
    is_mandatory = fields.Boolean(
        string='Is Mandatory?', default=True, tracking=True,
        help="Check if attendance for this session is mandatory for the certificate.")
    weight = fields.Float(
        string='Session Weight', default=1.0, tracking=True,
        help="Weight of this session for progress calculation.")
    
    online_meeting_url = fields.Char(
        string='Online Meeting URL',
        help="Override/shortcut for the meeting link. If empty, the link from the event will be used.")

    title = fields.Char(string='Title', related='event_id.name', readonly=True)
    date_start = fields.Datetime(string='Date Start', related='event_id.date_begin', readonly=True)
    date_end = fields.Datetime(string='Date End', related='event_id.date_end', readonly=True)
    instructor_id = fields.Many2one('res.partner', string='Instructor / Speaker')
    notes = fields.Text(string='Notes')
    qr_code_image = fields.Binary("QR Code", compute='_compute_qr_code')

    participant_count = fields.Integer(compute='_compute_related_counts')
    attendance_count = fields.Integer(compute='_compute_related_counts')
    assignment_count = fields.Integer(compute='_compute_related_counts')

    access_token = fields.Char(
        'Access Token', 
        required=True, 
        readonly=True, 
        index=True, 
        copy=False,
        default=lambda self: str(uuid.uuid4())
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
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
                qr_url = f'{base_url}/ojt/attend/{rec.access_token}'
                img = qrcode.make(qr_url)
                temp = io.BytesIO()
                img.save(temp, format="PNG")
                rec.qr_code_image = base64.b64encode(temp.getvalue())
            else:
                rec.qr_code_image = False

    @api.model_create_multi
    def create(self, vals):
        new_event_link = super(OjtEventLink, self).create(vals)

        template = self.env.ref('solvera_ojt_core.mail_template_new_ojt_agenda', raise_if_not_found=False)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        if template and new_event_link.batch_id.participant_ids:
            for participant in new_event_link.batch_id.participant_ids:
                if participant.partner_id.email:
                    autolog_url = f"{base_url}/my/agenda/join/{new_event_link.id}"
                    email_context = {
                        'participant_name_placeholder': participant.partner_id.name,
                        'participant_email_placeholder': participant.partner_id.email,
                        'autolog_join_url': autolog_url
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

    def action_mark_absentees(self):
        attendance = self.env['ojt.attendance']
        for session in self:
            if not session.batch_id:
                continue

            all_participants = session.batch_id.participant_ids

            attended_participant_ids = attendance.search([
                ('event_link_id', '=', session.id)
            ]).mapped('participant_id')

            absentee_participants = all_participants - attended_participant_ids

            if not absentee_participants:
                raise models.UserError("Semua peserta sudah tercatat kehadirannya.")

            attendance_vals_list = []
            for participant in absentee_participants:
                attendance_vals_list.append({
                    'participant_id': participant.id,
                    'event_link_id': session.id,
                    'batch_id': session.batch_id.id,
                    'event_id': session.event_id.id,
                    'check_in': fields.Datetime.now(),
                    'presence': 'absent',
                    'method': 'manual',
                })

            attendance.create(attendance_vals_list)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Proses Selesai',
                    'message': f'{len(absentee_participants)} peserta telah ditandai sebagai "Absent".',
                    'type': 'success',
                }
            }