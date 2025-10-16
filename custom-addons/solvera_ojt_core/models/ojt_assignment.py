# -*- coding: utf-8 -*-
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class OjtAssignment(models.Model):
    _name = 'ojt.assignment'
    _description = 'OJT Task/Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)

    participant_id = fields.Many2one('ojt.participant', string="Participant", require=False)
    
    batch_id = fields.Many2one(
        'ojt.batch', string='OJT Batch', 
        related='participant_id.batch_id', store=True, readonly=False)
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='participant_id.company_id', store=True, readonly=True)

    event_link_id = fields.Many2one('ojt.event.link', string='Related Session', help="If this assignment is specific to a certain session.")
    
    description = fields.Html(string='Description')
    
    type = fields.Selection([
        ('task', 'Task/Project'),
        ('quiz', 'Quiz (Survey/Slides)'),
        ('presentation', 'Presentation')
    ], string='Type', default='task', required=True)
    
    deadline = fields.Datetime(string='Deadline')
    max_score = fields.Float(string='Max Score', default=100.0)
    weight = fields.Float(string='Weight', default=1.0, help="Weight for final score calculation.")
    attachment_required = fields.Boolean(string='Attachment Required?', default=True)
    
    submit_ids = fields.One2many('ojt.assignment.submit', 'assignment_id', string='Submissions')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    def action_open(self):
        """Sets the assignment state to 'Open'."""
        return self.write({'state': 'open'})

    def action_close(self):
        """Sets the assignment state to 'Closed'."""
        return self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        """Resets the assignment state to 'Draft'."""
        return self.write({'state': 'draft'})
        
    def _cron_close_past_deadline_assignments(self):
        """
        Cron job to automatically close assignments that are past their deadline.
        """
        assignments_to_close = self.search([
            ('state', '=', 'open'),
            ('deadline', '!=', False),
            ('deadline', '<', fields.Datetime.now())
        ])
        
        if assignments_to_close:
            _logger.info(f"OJT Cron: Closing {len(assignments_to_close)} assignments past their deadline.")
            assignments_to_close.action_close()