# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class OjtParticipant(models.Model):
    _name = 'ojt.participant'
    _description = 'OJT Participant'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True, index=True)
    
    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, ondelete='cascade', tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Participant', required=True, tracking=True,
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
    
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'),
        ('failed', 'Failed'), ('left', 'Left')
    ], string='Status', default='active', tracking=True)

    submission_ids = fields.One2many('ojt.assignment.submit', 'participant_id', string='Assignment Submissions')
    attendance_ids = fields.One2many('ojt.attendance', 'participant_id', string='Attendance Records')
    certificate_ids = fields.One2many('ojt.certificate', 'participant_id', string='Certificates')
    course_ids = fields.Many2many(
        'slide.channel', 'ojt_participant_channel_rel', 'participant_id', 
        'channel_id', string='eLearning Enrollments')

    attendance_count = fields.Integer(string="Presents", compute='_compute_attendance_rate', store=True)
    attendance_rate = fields.Float(string="Attendance Rate (%)", compute='_compute_attendance_rate', store=True, group_operator="avg")
    score_avg = fields.Float(string='Average Score', compute='_compute_scores', store=True, digits=(16, 2))
    score_final = fields.Float(string='Final Score', compute='_compute_scores', store=True, digits=(16, 2))
    
    assignment_submit_count = fields.Integer(compute='_compute_related_counts')
    certificate_count = fields.Integer(compute='_compute_related_counts')
    course_count = fields.Integer(compute='_compute_related_counts')
    survey_count = fields.Integer(compute='_compute_related_counts')

    mentor_score = fields.Float(string="Mentor Score", tracking=True, help="Nilai akhir atau evaluasi dari mentor terhadap peserta.")
    portal_token = fields.Char(string='Portal Access Token', index=True, copy=False)
    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    access_url = fields.Char(
        'Portal URL', compute='_compute_access_url',
        help='URL yang digunakan oleh pelanggan untuk mengakses record ini dari portal.')
    
    def _compute_access_url(self):
        super(OjtParticipant, self)._compute_access_url()
        for participant in self:
            participant.access_url = '/my/dashboard'

    def write(self, vals):
        participants_to_notify = self.browse()
        if 'mentor_score' in vals and vals.get('mentor_score'):
            participants_to_notify = self.filtered(lambda p: not p.mentor_score)

        res = super(OjtParticipant, self).write(vals)

        if participants_to_notify:
            participants_to_notify._send_mentor_score_notification()
            
        return res
    
    def _send_mentor_score_notification(self):
        template = self.env.ref('solvera_ojt_core.mail_template_mentor_score', raise_if_not_found=False)
        if not template:
            return

        for participant in self:
            if participant.partner_id.email:
                portal_url = participant.get_portal_url(query_string=f'participant_id={participant.id}')
                
                template_ctx = {'url_portal_dashboard': portal_url}
                template.with_context(template_ctx).send_mail(
                    participant.id,
                    force_send=True
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'batch_id' in vals and vals['batch_id']:
                batch = self.env['ojt.batch'].browse(vals['batch_id'])
                
                if batch.state in ['ongoing', 'done', 'cancel']:
                    raise ValidationError(
                        f"You cannot add new participants to the batch '{batch.name}' "
                        f"because its status is '{batch.state}'."
                    )
                    
        return super(OjtParticipant, self).create(vals_list)
    
    @api.depends('partner_id.name', 'batch_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.partner_id.name} - {rec.batch_id.name}" if rec.partner_id and rec.batch_id else "/"
    
    @api.depends('submission_ids', 'certificate_ids', 'course_ids', 'partner_id', 'batch_id.survey_id')
    def _compute_related_counts(self):
        """ Efficiently computes all smart button counters in one go. """
        for rec in self:
            rec.assignment_submit_count = len(rec.submission_ids)
            rec.certificate_count = len(rec.certificate_ids)
            rec.course_count = len(rec.course_ids)
            if rec.partner_id and rec.batch_id.survey_id:
                rec.survey_count = self.env['survey.user_input'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('survey_id', '=', rec.batch_id.survey_id.id)
                ])
            else:
                rec.survey_count = 0

    @api.depends('attendance_ids.presence', 'batch_id.event_link_ids.is_mandatory')
    def _compute_attendance_rate(self):
        for rec in self:
            mandatory_sessions = rec.batch_id.event_link_ids.filtered(lambda l: l.is_mandatory)
            total_mandatory_sessions = len(mandatory_sessions)
            
            present_attendances = rec.attendance_ids.filtered(
                lambda a: a.event_link_id.is_mandatory and a.presence in ('present', 'late'))
            rec.attendance_count = len(present_attendances)

            rec.attendance_rate = (rec.attendance_count / total_mandatory_sessions) * 100.0 if total_mandatory_sessions > 0 else 0.0
            
    @api.depends('submission_ids.score', 'submission_ids.state', 
                    'submission_ids.assignment_id.weight', 'submission_ids.assignment_id.max_score', 
                    'mentor_score', 'batch_id.survey_id')
    def _compute_scores(self):
        weight_assignment, weight_mentor, weight_quiz = 0.7, 0.2, 0.1
        for participant in self:
            scored_submissions = participant.submission_ids.filtered(lambda s: s.state == 'scored')
            total_weighted_score, total_weight = 0.0, 0.0
            if scored_submissions:
                for sub in scored_submissions:
                    assignment = sub.assignment_id
                    if assignment.max_score > 0 and assignment.weight > 0:
                        normalized_score = (sub.score / assignment.max_score) * 100.0
                        total_weighted_score += normalized_score * assignment.weight
                        total_weight += assignment.weight
                participant.score_avg = total_weighted_score / total_weight if total_weight > 0 else 0.0
            else:
                participant.score_avg = 0.0
            
            quiz_score = 0.0
            if participant.batch_id.survey_id and participant.partner_id:
                survey_input = self.env['survey.user_input'].search([
                    ('survey_id', '=', participant.batch_id.survey_id.id),
                    ('partner_id', '=', participant.partner_id.id),
                    ('state', '=', 'done')
                ], limit=1, order='create_date desc')
                if survey_input:
                    quiz_score = survey_input.scoring_percentage

            participant.score_final = (participant.score_avg * weight_assignment) + \
                                      (participant.mentor_score * weight_mentor) + \
                                      (quiz_score * weight_quiz)

    def action_open_assignments(self):
        self.ensure_one()
        return {
            'name': 'Assignments', 'type': 'ir.actions.act_window', 'res_model': 'ojt.assignment.submit',
            'view_mode': 'list,form', 'domain': [('participant_id', '=', self.id)],
        }

    def action_open_attendance(self):
        self.ensure_one()
        return {
            'name': 'Attendance', 'type': 'ir.actions.act_window', 'res_model': 'ojt.attendance',
            'view_mode': 'list,form', 'domain': [('participant_id', '=', self.id)],
        }

    def action_open_certificates(self):
        self.ensure_one()
        return {
            'name': 'Certificates', 'type': 'ir.actions.act_window', 'res_model': 'ojt.certificate',
            'view_mode': 'list,form', 'domain': [('participant_id', '=', self.id)],
        }

    def action_open_survey_results(self):
        self.ensure_one()
        tree_view_id = self.env.ref('survey.survey_user_input_view_tree').id
        form_view_id = self.env.ref('survey.survey_user_input_view_form').id
        return {
            'name': 'Survey Results', 'type': 'ir.actions.act_window', 'res_model': 'survey.user_input',
            'view_mode': 'tree,form', 'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('survey_id', '=', self.batch_id.survey_id.id)
            ],
        }