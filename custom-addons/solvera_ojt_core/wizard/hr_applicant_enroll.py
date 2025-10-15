# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrApplicantEnroll(models.TransientModel):
    _name = 'hr.applicant.enroll.wizard'
    _description = 'Wizard to Enroll Applicant to OJT Batch'

    # Field ini akan menampung semua pelamar yang dipilih dari list view
    applicant_ids = fields.Many2many('hr.applicant', string='Applicants', readonly=True)
    batch_id = fields.Many2one('ojt.batch', string='Target OJT Batch', required=True,
                                domain="[('state', 'in', ['draft', 'recruit'])]")

    def action_enroll(self):
        self.ensure_one()
        participant_obj = self.env['ojt.participant']
        ojt_stage = self.env['hr.recruitment.stage'].search([('name', '=ilike', 'OJT')], limit=1)
        
        # Ambil template email di luar loop agar efisien
        template = self.env.ref('solvera_ojt_core.mail_template_ojt_portal_invitation', raise_if_not_found=False)

        for applicant in self.applicant_ids:
            partner = applicant.partner_id
            if not partner:
                if not applicant.partner_name:
                    continue
                partner = self.env['res.partner'].search([('email', '=ilike', applicant.email_from)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': applicant.partner_name,
                        'email': applicant.email_from,
                        'phone': applicant.partner_phone,
                    })
                applicant.partner_id = partner.id

            if not participant_obj.search([('applicant_id', '=', applicant.id), ('batch_id', '=', self.batch_id.id)]):
                new_participant = participant_obj.create({
                    'partner_id': partner.id,
                    'batch_id': self.batch_id.id,
                    'applicant_id': applicant.id,
                    'state': 'active',
                })

                # --- LOGIKA PENGIRIMAN EMAIL SEKARANG AKTIF ---
                if template and new_participant:
                    # Kirim email untuk participant yang baru dibuat
                    template.send_mail(new_participant.id, force_send=True)

        # Pindahkan stage semua applicant yang diproses
        if ojt_stage:
            self.applicant_ids.write({'stage_id': ojt_stage.id})
        
        return {'type': 'ir.actions.act_window_close'}