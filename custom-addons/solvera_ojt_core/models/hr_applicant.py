# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    batch_id = fields.Many2one('ojt.batch', string='Target OJT Batch',
                                domain="[('state', 'in', ['draft', 'recruit'])]")
    
    portal_status = fields.Selection([
        ('pending', 'Pending'),
        ('shortlisted', 'In Process'),
        ('accepted', 'Accepted'),
        ('rejected', 'Not Retained'),
    ], string="Portal Status", compute='_compute_portal_status')

    def action_open_enroll_wizard(self):
        self.ensure_one()
        
        # Pengecekan keamanan di sisi server
        if self.stage_id.name.lower() != 'new':
            raise UserError("You can only enroll an applicant from a 'New' stage.")

        # Membuka wizard
        action = self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_hr_applicant_enroll_wizard_window')
        action['context'] = {'default_applicant_ids': self.ids}
        return action

    def write(self, vals):
        # Cek apakah 'stage_id' sedang diubah
        if 'stage_id' in vals:
            # Periksa "kunci rahasia". Jika kunci ini ada, lewati validasi.
            if not self.env.context.get('enroll_from_wizard'):
                new_stage = self.env['hr.recruitment.stage'].browse(vals.get('stage_id'))
                # Ini adalah aturan validasi Anda yang sudah ada
                if new_stage and 'ojt' in new_stage.name.lower():
                    raise ValidationError("Anda tidak dapat memindahkan pelamar ke stage 'OJT' secara manual. Gunakan tombol 'Enroll to OJT' untuk melanjutkan.")

        # Jalankan proses write asli (termasuk logika otomatisasi Anda)
        res = super(HrApplicant, self).write(vals)

        # Lakukan pengecekan SETELAH data tersimpan
        new_stage_after_write = self.env['hr.recruitment.stage'].browse(vals.get('stage_id')) if vals.get('stage_id') else None
        for applicant in self:
            if new_stage_after_write and new_stage_after_write.hired_stage and applicant.batch_id:
                self.env['hr.applicant.enroll.wizard'].create({
                    'applicant_ids': [(4, applicant.id)],
                    'batch_id': applicant.batch_id.id,
                }).action_enroll()
                
        return res
        
    @api.depends('stage_id', 'stage_id.hired_stage')
    def _compute_portal_status(self):
        # Anda bisa menyesuaikan logika ini sesuai dengan nama stage Anda
        # Ini hanya contoh sederhana
        for applicant in self:
            if applicant.stage_id.hired_stage:
                applicant.portal_status = 'accepted'
            elif applicant.stage_id.sequence == 1: # Asumsi stage pertama adalah 'Pending'
                applicant.portal_status = 'pending'
            # Anda perlu cara untuk menandai stage 'Rejected'. 
            # Untuk saat ini, kita bisa asumsikan dari namanya.
            elif 'refuse' in applicant.stage_id.name.lower() or 'rejected' in applicant.stage_id.name.lower():
                applicant.portal_status = 'rejected'
            else: # Stage lainnya kita anggap 'In Process'
                applicant.portal_status = 'shortlisted'