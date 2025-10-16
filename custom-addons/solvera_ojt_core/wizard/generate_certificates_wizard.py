from odoo import models, fields, api

class GenerateCertificatesWizard(models.TransientModel):
    _name = 'ojt.generate.certificates.wizard'
    _description = 'Wizard to Generate Certificates for Eligible Participants'

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', readonly=True, required=True)
    
    eligible_participant_ids = fields.Many2many(
        'ojt.participant', 
        string='Eligible Participants', 
        compute='_compute_eligible_participants',
        readonly=True
    )
    participant_count = fields.Integer(compute='_compute_eligible_participants')

    overwrite_existing = fields.Boolean(
        string='Overwrite Existing Certificates', 
        help="If checked, new certificates will be created even for participants who already have one."
    )

    @api.depends('batch_id')
    def _compute_eligible_participants(self):
        for wizard in self:
            if wizard.batch_id:
                domain = [
                    ('batch_id', '=', wizard.batch_id.id),
                    ('state', '=', 'completed'),
                    ('attendance_rate', '>=', wizard.batch_id.certificate_rule_attendance),
                    ('score_final', '>=', wizard.batch_id.certificate_rule_score),
                ]
                eligible_participants = self.env['ojt.participant'].search(domain)
                wizard.eligible_participant_ids = [(6, 0, eligible_participants.ids)]
                wizard.participant_count = len(eligible_participants)
            else:
                wizard.eligible_participant_ids = False
                wizard.participant_count = 0

    def action_generate_certificates(self):
        self.ensure_one()

        template = self.env.ref('solvera_ojt_core.mail_template_certificate_issued', raise_if_not_found=False)
        
        for participant in self.eligible_participant_ids:
            existing_certificate = self.env['ojt.certificate'].search([
                ('participant_id', '=', participant.id)
            ])
            
            if existing_certificate and not self.overwrite_existing:
                continue

            if existing_certificate and self.overwrite_existing:
                existing_certificate.unlink()

            new_certificate = self.env['ojt.certificate'].create({
                'name': f"Certificate for {participant.name}",
                'participant_id': participant.id,
                'batch_id': self.batch_id.id,
                'state': 'issued',
            })

            if template and new_certificate:
                new_certificate.action_issue()
                template.send_mail(new_certificate.id, force_send=True)
        
        return {'type': 'ir.actions.act_window_close'}