# -*- coding: utf-8 -*-
from odoo import models, fields, api

class OjtParticipant(models.Model):
    _name = 'ojt.participant'
    _description = 'OJT Participant'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True, index=True)
    
    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Participant', required=True, help="Link to the contact record of the participant.")
    applicant_id = fields.Many2one('hr.applicant', string='Recruitment Applicant', help="Original applicant record from recruitment.")
    
    # Placeholder for compute methods
    attendance_count = fields.Integer(string="Presents", compute='_compute_attendance_rate', store=True)
    attendance_rate = fields.Float(string="Attendance Rate (%)", compute='_compute_attendance_rate', store=True, group_operator="avg")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('left', 'Left')
    ], string='Status', default='active', track_visibility='onchange')

    assignment_submit_ids = fields.One2many('ojt.assignment.submit', 'participant_id', string='Assignment Submissions')
    attendance_ids = fields.One2many('ojt.attendance', 'participant_id', string='Attendance Records')
    
    # Relational fields to be defined later
    certificate_id = fields.One2many('ojt.certificate', 'participant_id', string='Certificate')

    portal_token = fields.Char(string='Portal Access Token', index=True, copy=False)
    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    submission_ids = fields.One2many('ojt.assignment.submit', 'participant_id', string='Submissions')
    score_avg = fields.Float(string='Average Score', compute='_compute_scores', store=True, digits=(16, 2))
    score_final = fields.Float(string='Final Score', compute='_compute_scores', store=True, digits=(16, 2))

    # Compute this field to combine partner and batch name for a unique display name
    @api.depends('partner_id', 'batch_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.partner_id.name} - {rec.batch_id.name}" if rec.partner_id and rec.batch_id else "/"
    
    @api.depends('attendance_ids', 'batch_id.event_link_ids')
    def _compute_attendance_rate(self):
        for rec in self:
            mandatory_sessions = rec.batch_id.event_link_ids.filtered(lambda l: l.is_mandatory)
            total_mandatory_sessions = len(mandatory_sessions)

            present_attendances = rec.attendance_ids.filtered(lambda a: a.presence in ('present', 'late'))
            rec.attendance_count = len(present_attendances)

            if total_mandatory_sessions > 0:
                rec.attendance_rate = (rec.attendance_count / total_mandatory_sessions) * 100.0
            else:
                rec.attendance_rate = 0.0
        
    @api.depends('submission_ids', 'submission_ids.score', 'submission_ids.state')
    def _compute_scores(self):
        """
        Calculates the average and final scores based on submitted assignments that have been scored.
        """
        for participant in self:
            # Ambil semua submission yang sudah dinilai (state = 'scored')
            scored_submissions = participant.submission_ids.filtered(lambda s: s.state == 'scored')
            
            if scored_submissions:
                # Hitung total nilai
                total_score = sum(scored_submissions.mapped('score'))
                # Hitung rata-rata
                average = total_score / len(scored_submissions)
                
                participant.score_avg = average
                # Untuk saat ini, nilai akhir sama dengan rata-rata.
                # Di masa depan, logika ini bisa diubah untuk memasukkan bobot tugas.
                participant.score_final = average
            else:
                # Jika belum ada tugas yang dinilai, set nilainya ke 0
                participant.score_avg = 0.0
                participant.score_final = 0.0