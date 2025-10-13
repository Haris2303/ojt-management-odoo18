# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class OjtAssignmentSubmit(models.Model):
    _name = 'ojt.assignment.submit'
    _description = 'OJT Assignment Submission'

    assignment_id = fields.Many2one('ojt.assignment', string='Assignment', required=True, ondelete='cascade')
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True, ondelete='cascade')
    
    submitted_on = fields.Datetime(string='Submitted On', default=fields.Datetime.now)
    
    # Using Many2many for attachments allows multiple file uploads
    attachment_ids = fields.Many2many('ir.attachment', 'ojt_assignment_submit_attachment_rel', 'submit_id', 'attachment_id', string='Attachments')
    url_link = fields.Char(string='URL Link', help="For submissions like Git, Figma, video, etc.")
    
    score = fields.Float(string='Score')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda self: self.env.user)
    feedback = fields.Html(string='Feedback')
    
    late = fields.Boolean(string='Submitted Late?', compute='_compute_late', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('scored', 'Scored')
    ], string='Status', default='submitted')

    @api.constrains('score', 'assignment_id')
    def _check_score(self):
        for sub in self:
            if sub.assignment_id and sub.score > sub.assignment_id.max_score:
                raise ValidationError(f"The score cannot be higher than the maximum score of {sub.assignment_id.max_score}.")

    @api.depends('submitted_on', 'assignment_id.deadline')
    def _compute_late(self):
        for sub in self:
            sub.late = sub.submitted_on and sub.assignment_id.deadline and sub.submitted_on > sub.assignment_id.deadline

    def action_mark_as_scored(self):
        """
        Marks the submission as 'Scored'.
        Also ensures a score has been given.
        """
        for sub in self:
            if not sub.score and sub.score != 0:
                raise ValidationError("You cannot mark a submission as scored without providing a score first.")
            sub.write({'state': 'scored'})
        return True

    def action_reset_to_submitted(self):
        """Resets the submission state back to 'Submitted'."""
        self.write({'state': 'submitted'})
        return True