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
        
        # Loop melalui semua pelamar yang dipilih
        for applicant in self.applicant_ids:
            # Lanjutkan dengan logika Anda yang sudah ada
            partner = applicant.partner_id
            if not partner:
                if not applicant.partner_name:
                    continue # Lewati jika tidak ada nama
                partner = self.env['res.partner'].search([('email', '=ilike', applicant.email_from)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': applicant.partner_name,
                        'email': applicant.email_from,
                        'phone': applicant.partner_phone,
                    })
                applicant.partner_id = partner.id

            # Cek duplikat sebelum membuat
            if not participant_obj.search([('applicant_id', '=', applicant.id), ('batch_id', '=', self.batch_id.id)]):
                participant_obj.create({
                    'partner_id': partner.id,
                    'batch_id': self.batch_id.id,
                    'applicant_id': applicant.id,
                    'state': 'active',
                })
        
        # Logika email bisa ditambahkan kembali di sini jika diperlukan
        # template = self.env.ref('solvera_ojt_core.mail_template_ojt_portal_invitation') ...

        return {'type': 'ir.actions.act_window_close'}