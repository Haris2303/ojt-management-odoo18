# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class OjtBatch(models.Model):
    _name = 'ojt.batch'
    _description = 'OJT Program Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Batch Name', required=True, index=True, help='Name of the batch, e.g., OJT BA Oct 2025')
    code = fields.Char(string='Batch Code', required=True, readonly=True, default='/', copy=False)
    job_id = fields.Many2one('hr.job', string='Related Position', help="The job position this OJT is for.")
    description = fields.Html(string='Description')
    department_id = fields.Many2one('hr.department', string='Organizing Division')
    mentor_ids = fields.Many2many('res.partner', 'ojt_batch_mentor_rel', 'batch_id', 'mentor_id', string='Mentors/Instructors')

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    mode = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid')
    ], string='Mode', default='online', required=True)
    
    capacity = fields.Integer(string='Target Capacity', help="Target number of participants.")

    participant_ids = fields.One2many('ojt.participant', 'batch_id', string='Participants')
    event_link_ids = fields.One2many('ojt.event.link', 'batch_id', string='Agenda/Events')
    course_ids = fields.Many2many('slide.channel', 'ojt_batch_channel_rel', 'batch_id', 'channel_id', string='eLearning Courses')
    survey_id = fields.Many2one('survey.survey', string='Evaluation Survey')

    participant_count = fields.Integer(string="Participant Count", compute='_compute_counts')
    event_link_count = fields.Integer(string="Event Count", compute='_compute_counts')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('recruit', 'Recruitment'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    certificate_rule_attendance = fields.Float(string='Min. Attendance (%)', default=80.0)
    certificate_rule_score = fields.Float(string='Min. Final Score', default=70.0)
    
    progress_ratio = fields.Float(string='Average Progress', compute='_compute_progress_ratio', store=True)
    
    color = fields.Integer(string='Color Index')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    active = fields.Boolean(default=True)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for batch in self:
            if batch.start_date and batch.end_date and batch.start_date > batch.end_date:
                raise ValidationError("The start date cannot be later than the end date.")

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('ojt.batch') or '/'
        return super(OjtBatch, self).create(vals)

    def write(self, vals):
        if 'state' in vals:
            new_state = vals['state']
            for batch in self:
                if batch.state == 'done' and new_state in ['draft', 'recruit']:
                    participants_to_revert = batch.participant_ids.filtered(lambda p: p.state == 'completed')
                    if participants_to_revert:
                        participants_to_revert.write({'state': 'active'})
        return super(OjtBatch, self).write(vals)

    @api.depends('participant_ids', 'event_link_ids')
    def _compute_counts(self):
        for batch in self:
            batch.participant_count = len(batch.participant_ids)
            batch.event_link_count = len(batch.event_link_ids)

    @api.depends('participant_ids.score_final')
    def _compute_progress_ratio(self):
        for batch in self:
            if batch.participant_ids:
                average_score = sum(batch.participant_ids.mapped('score_final')) / len(batch.participant_ids)
                batch.progress_ratio = average_score
            else:
                batch.progress_ratio = 0.0

    def action_recruit(self):
        return self.write({'state': 'recruit'})

    def action_ongoing(self):
        return self.write({'state': 'ongoing'})

    def action_done(self):
        self.participant_ids.write({'state': 'completed'})
        return self.write({'state': 'done'})

    @api.model
    def _cron_update_batch_states(self):
        _logger.info("Cron: Starting batch state update...")
        today = fields.Date.today()
        
        ongoing_batches_to_close = self.search([('state', '=', 'ongoing'), ('end_date', '<', today)])
        if ongoing_batches_to_close:
            ongoing_batches_to_close.action_done()
            _logger.info(f"Cron: Moved {len(ongoing_batches_to_close)} batches to 'Done'.")

        recruiting_batches_to_start = self.search([('state', '=', 'recruit'), ('start_date', '<=', today)])
        if recruiting_batches_to_start:
            recruiting_batches_to_start.action_ongoing()
            _logger.info(f"Cron: Moved {len(recruiting_batches_to_start)} batches to 'Ongoing'.")
        
        _logger.info("Cron: Batch state update finished.")
        return True

    def action_open_generate_certificates_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Certificates',
            'res_model': 'ojt.generate.certificates.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_id': self.id}
        }

    def action_view_participants(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_ojt_participant_from_batch')
        return action

    def action_view_agenda(self):
        self.ensure_one()
        return self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_ojt_event_link_from_batch')
        # action['domain'] = [('batch_id', '=', self.id)]
        # action['context'] = {'default_batch_id': self.id}
        # return action