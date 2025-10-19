# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OjtAssignmentSubmit(models.Model):
    _name = 'ojt.assignment.submit'
    _description = 'OJT Assignment Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    assignment_id = fields.Many2one('ojt.assignment', string='Assignment', required=True, ondelete='cascade')
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True, ondelete='cascade')
    
    submitted_on = fields.Datetime(string='Submitted On', default=fields.Datetime.now, readonly=True)
    
    attachment_ids = fields.Many2many(
        'ir.attachment', 'ojt_assignment_submit_attachment_rel', 
        'submit_id', 'attachment_id', string='Attachments')
    url_link = fields.Char(string='URL Link', help="For submissions like Git, Figma, video, etc.")
    
    score = fields.Float(string='Score', tracking=True) # Ditambahkan tracking
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda self: self.env.user, tracking=True)
    feedback = fields.Html(string='Feedback')
    
    late = fields.Boolean(string='Submitted Late?', compute='_compute_late', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('scored', 'Scored')
    ], string='Status', default='submitted', tracking=True) # Ditambahkan tracking

    access_url = fields.Char('Portal URL', compute='_compute_access_url')

    @api.constrains('score', 'assignment_id')
    def _check_score(self):
        for sub in self:
            if sub.assignment_id and sub.score and sub.assignment_id.max_score and sub.score > sub.assignment_id.max_score:
                raise ValidationError(f"The score ({sub.score}) cannot be higher than the maximum score of {sub.assignment_id.max_score}.")

    @api.depends('submitted_on', 'assignment_id.deadline')
    def _compute_late(self):
        for sub in self:
            sub.late = bool(sub.submitted_on and sub.assignment_id.deadline and sub.submitted_on > sub.assignment_id.deadline)

    def _compute_access_url(self):
        super(OjtAssignmentSubmit, self)._compute_access_url()
        for submission in self:
            submission.access_url = f'/my/assignment/{submission.id}'
    
    def write(self, vals):
        submissions_to_notify = self.browse()
        # Deteksi jika state diubah menjadi 'scored'
        if vals.get('state') == 'scored':
            submissions_to_notify = self.filtered(lambda s: s.state != 'scored')

        res = super(OjtAssignmentSubmit, self).write(vals)

        if submissions_to_notify:
            _logger.info(f"Terdeteksi {len(submissions_to_notify)} pengumpulan tugas yang dinilai. Mengirim notifikasi...")
            submissions_to_notify._send_scored_notification()
            
        return res
    
    def _send_scored_notification(self):
        """Mengirim notifikasi email saat tugas sudah dinilai."""
        template = self.env.ref('solvera_ojt_core.mail_template_assignment_scored', raise_if_not_found=False)
        if not template:
            _logger.error("Template email 'mail_template_assignment_scored' tidak ditemukan.")
            return

        for submission in self:
            if submission.participant_id.partner_id.email:
                portal_url = submission.get_portal_url()
                template_ctx = {'url_portal_submission': portal_url}
                template.with_context(template_ctx).send_mail(
                    submission.id,
                    force_send=True
                )

    def action_mark_as_scored(self):
        """
        Marks the submission as 'Scored' and validates that a score is present.
        """
        for sub in self:
            if sub.score is None or sub.score < 0:
                raise ValidationError("You must provide a valid score before marking as 'Scored'.")
            sub.write({'state': 'scored'})
        return True

    def action_reset_to_submitted(self):
        """Resets the submission state back to 'Submitted'."""
        self.write({'state': 'submitted'})
        return True