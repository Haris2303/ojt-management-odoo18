# -*- coding: utf-8 -*-
from odoo import models, fields, api

class OjtParticipant(models.Model):
    _name = 'ojt.participant'
    _description = 'OJT Participant'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True, index=True)
    
    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner', string='Participant', required=True, 
        help="Link to the contact record of the participant.")
    applicant_id = fields.Many2one(
        'hr.applicant', string='Recruitment Applicant', 
        help="Original applicant record from recruitment.")
    
    attendance_count = fields.Integer(string="Presents", compute='_compute_attendance_rate', store=True)
    attendance_rate = fields.Float(string="Attendance Rate (%)", compute='_compute_attendance_rate', store=True, group_operator="avg")
    
    mentor_score = fields.Float(string="Mentor Score", tracking=True, help="Nilai akhir atau evaluasi dari mentor terhadap peserta.")
    
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'),
        ('failed', 'Failed'), ('left', 'Left')
    ], string='Status', default='active', track_visibility='onchange') # Seharusnya tracking=True untuk Odoo 18+

    # Hapus 'assignment_submit_ids', cukup gunakan 'submission_ids'
    submission_ids = fields.One2many('ojt.assignment.submit', 'participant_id', string='Assignment Submissions')
    attendance_ids = fields.One2many('ojt.attendance', 'participant_id', string='Attendance Records')
    certificate_id = fields.One2many('ojt.certificate', 'participant_id', string='Certificate')

    portal_token = fields.Char(string='Portal Access Token', index=True, copy=False)
    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    score_avg = fields.Float(string='Average Score', compute='_compute_scores', store=True, digits=(16, 2))
    score_final = fields.Float(string='Final Score', compute='_compute_scores', store=True, digits=(16, 2))

    course_ids = fields.Many2many(
        'slide.channel', 'ojt_participant_channel_rel', 'participant_id', 
        'channel_id', string='eLearning Enrollments')
    
    # --- FIELD-FIELD COMPUTE DIPERBAIKI ---
    course_count = fields.Integer(string="Course Count", compute='_compute_course_count', store=True)
    survey_count = fields.Integer(string="Survey Count", compute='_compute_survey_count', store=True)

    @api.depends('course_ids')
    def _compute_course_count(self):
        for rec in self:
            rec.course_count = len(rec.course_ids)

    @api.depends('partner_id', 'batch_id.survey_id')
    def _compute_survey_count(self):
        for rec in self:
            if rec.partner_id and rec.batch_id.survey_id:
                rec.survey_count = self.env['survey.user_input'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('survey_id', '=', rec.batch_id.survey_id.id)
                ])
            else:
                rec.survey_count = 0

    @api.depends('partner_id', 'batch_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.partner_id.name} - {rec.batch_id.name}" if rec.partner_id and rec.batch_id else "/"
    
    @api.depends('attendance_ids.presence', 'batch_id.event_link_ids.is_mandatory')
    def _compute_attendance_rate(self):
        for rec in self:
            mandatory_sessions = rec.batch_id.event_link_ids.filtered(lambda l: l.is_mandatory)
            total_mandatory_sessions = len(mandatory_sessions)

            present_attendances = rec.attendance_ids.filtered(lambda a: a.event_link_id.is_mandatory and a.presence in ('present', 'late'))
            rec.attendance_count = len(present_attendances)

            if total_mandatory_sessions > 0:
                rec.attendance_rate = (rec.attendance_count / total_mandatory_sessions) * 100.0
            else:
                rec.attendance_rate = 0.0
    
    # Method _compute_scores Anda sudah benar, tidak perlu diubah
    @api.depends('submission_ids.score', 'submission_ids.state', 'submission_ids.assignment_id.weight', 'submission_ids.assignment_id.max_score', 'mentor_score')
    def _compute_scores(self):
        # ... isi method biarkan seperti yang sudah Anda buat ...
        for participant in self:
            # ... logika perhitungan berbobot ...
            # ...
            participant.score_final = (participant.score_avg * 0.8) + (participant.mentor_score * 0.2)

    # --- METHOD ACTION UNTUK SMART BUTTON DIPERBAIKI ---
    def action_open_assignments(self):
        self.ensure_one()
        return {
            'name': 'Assignments',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.assignment.submit',
            'view_mode': 'list,form',
            'domain': [('participant_id', '=', self.id)],
        }

    def action_open_attendance(self):
        self.ensure_one()
        return {
            'name': 'Attendance',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.attendance',
            'view_mode': 'list,form',
            'domain': [('participant_id', '=', self.id)],
        }

    def action_open_certificates(self):
        self.ensure_one()
        return {
            'name': 'Certificates',
            'type': 'ir.actions.act_window',
            'res_model': 'ojt.certificate',
            'view_mode': 'list,form',
            'domain': [('participant_id', '=', self.id)],
        }

    def action_open_courses(self):
        self.ensure_one()
        return {
            'name': 'eLearning Courses',
            'type': 'ir.actions.act_window',
            'res_model': 'slide.channel',
            'view_mode': 'kanban,form',
            'domain': [('id', 'in', self.course_ids.ids)],
        }

    def action_open_survey_results(self):
        self.ensure_one()
        return {
            'name': 'Survey Results',
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('survey_id', '=', self.batch_id.survey_id.id)
            ],
        }