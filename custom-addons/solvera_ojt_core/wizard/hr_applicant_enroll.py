# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrApplicantEnroll(models.TransientModel):
    _name = 'hr.applicant.enroll.wizard'
    _description = 'Wizard to Enroll Applicant to OJT Batch'

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, domain="[('state', '=', 'recruit')]")

    def action_enroll(self):
        self.ensure_one()
        applicant_id = self.env.context.get('active_id')
        applicant = self.env['hr.applicant'].browse(applicant_id)

        if not applicant.partner_name:
            raise ValidationError("Applicant must have a contact name.")

        # Find or create a partner for the applicant
        partner = self.env['res.partner'].search([('email', '=ilike', applicant.email_from)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': applicant.partner_name,
                'email': applicant.email_from,
                'phone': applicant.partner_phone,
            })

        # Create the OJT participant record
        participant = self.env['ojt.participant'].create({
            'partner_id': partner.id,
            'batch_id': self.batch_id.id,
            'applicant_id': applicant.id,
            'state': 'active',
        })

        template = self.env.ref('solvera_ojt_core.mail_template_ojt_portal_invitation')
        if template:
            # Send email
            template.send_mail(participant.id, force_send=True)

        # You might want to automatically change the applicant stage here
        # For example, move to a "Enrolled in OJT" stage if you have one.

        return {'type': 'ir.actions.act_window_close'}