# -*- coding: utf-8 -*-
import logging
from odoo.exceptions import ValidationError
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class OjtAssignment(models.Model):
    _name = 'ojt.assignment'
    _description = 'OJT Task/Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)

    batch_id = fields.Many2one(
        'ojt.batch', 
        string='OJT Batch', 
        store=True, 
        readonly=False, 
        required=True, 
        domain="[('state', '=', 'ongoing')]"
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='batch_id.company_id', store=True, readonly=True)

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

    access_url = fields.Char(
        'Portal URL', compute='_compute_access_url',
        help='URL portal untuk tugas ini.')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super(OjtAssignment, self).create(vals_list)
        return assignments
    
    def write(self, vals):
        assignments_to_notify = self.browse()
        if vals.get('state') == 'open':
            assignments_to_notify = self.filtered(lambda a: a.state != 'open')

        res = super(OjtAssignment, self).write(vals)

        if assignments_to_notify:
            _logger.info(f"Terdeteksi {len(assignments_to_notify)} tugas yang diubah menjadi 'Open'. Mengirim notifikasi...")
            assignments_to_notify._send_new_assignment_notification()
            
        return res

    def _compute_access_url(self):
        super(OjtAssignment, self)._compute_access_url()
        for assignment in self:
            assignment.access_url = f'/my/assignment/{assignment.id}'

    def _send_new_assignment_notification(self):
        
        try:
            template = self.env.ref('solvera_ojt_core.mail_template_new_assignment')
        except ValueError:
            return

        for assignment in self:
            if not assignment.batch_id:
                continue

            portal_url = assignment.get_portal_url()
            if not portal_url:
                continue

            for participant in assignment.batch_id.participant_ids:
                if not participant.partner_id.email:
                    _logger.warning(f"-> [DILEWATI] Peserta '{participant.name}' tidak memiliki alamat email.")
                    continue

                email_penerima = participant.partner_id.email
                _logger.info(f"--> [MENGIRIM] Mencoba mengirim email ke {email_penerima} untuk peserta '{participant.name}'...")

                template_ctx = {
                    'url_portal_assignment': portal_url,
                    'participant_name': participant.name,
                }

                template.with_context(template_ctx).send_mail(
                    assignment.id,
                    force_send=True,
                    email_values={'email_to': email_penerima} 
                )


    def action_open(self):
        
        for assignment in self:
            if assignment.state != 'open':
                
                assignment.write({'state': 'open'})
                
        return True

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

    @api.constrains('deadline')
    def _check_deadline(self):
        """
        Mencegah user mengatur deadline ke tanggal yang sudah lewat.
        """
        for assignment in self:
            if assignment.deadline and assignment.deadline < fields.Datetime.now():
                raise ValidationError("Deadline tidak boleh diatur ke tanggal yang sudah berlalu.")