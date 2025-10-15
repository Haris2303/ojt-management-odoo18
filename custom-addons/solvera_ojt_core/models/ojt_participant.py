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
    
    applicant_email = fields.Char(
        string='Applicant Email',
        related='applicant_id.email_from',
        store=True,
        readonly=True
    )
    
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
    
    # --- FIELD-FIELD COMPUTE DIPERBAIKI ---
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
        # Tentukan bobot
        weight_assignment = 0.7
        weight_mentor = 0.2
        weight_quiz = 0.1

        for participant in self:
            # 1. Hitung rata-rata berbobot dari tugas (logika ini sudah benar)
            scored_submissions = participant.submission_ids.filtered(lambda s: s.state == 'scored')
            total_weighted_score = 0.0
            total_weight = 0.0
            if scored_submissions:
                for sub in scored_submissions:
                    assignment = sub.assignment_id
                    if assignment.max_score > 0 and assignment.weight > 0:
                        normalized_score = (sub.score / assignment.max_score) * 100.0
                        total_weighted_score += normalized_score * assignment.weight
                        total_weight += assignment.weight
                
                if total_weight > 0:
                    participant.score_avg = total_weighted_score / total_weight
                else:
                    participant.score_avg = 0.0
            else:
                participant.score_avg = 0.0
            
            # 2. Ambil nilai kuis dari survei
            quiz_score = 0.0
            if participant.batch_id.survey_id and participant.partner_id:
                # Cari jawaban survei yang sudah selesai untuk peserta ini
                survey_input = self.env['survey.user_input'].search([
                    ('survey_id', '=', participant.batch_id.survey_id.id),
                    ('partner_id', '=', participant.partner_id.id),
                    ('state', '=', 'done')
                ], limit=1, order='create_date desc')
                if survey_input:
                    quiz_score = survey_input.scoring_percentage

            # 3. Hitung nilai akhir gabungan
            final_score = (participant.score_avg * weight_assignment) + \
                          (participant.mentor_score * weight_mentor) + \
                          (quiz_score * weight_quiz)
            
            participant.score_final = final_score

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