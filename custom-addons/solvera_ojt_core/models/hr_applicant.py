# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

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
        self.ensure_one() # Memastikan aksi hanya dijalankan pada satu record
        
        # --- PENGECEKAN DI SINI ---
        # Jika stage dari pelamar ini BUKAN 'hired_stage', tampilkan pesan error
        if not self.stage_id.hired_stage:
            raise UserError("You can only enroll an applicant from a 'Hired' stage.")

        # Jika lolos pengecekan, lanjutkan membuka wizard seperti biasa
        action = self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_hr_applicant_enroll_wizard_window')
        action['context'] = {'active_ids': self.ids}
        return action

    def write(self, vals):
        # Ambil stage baru jika ada perubahan
        new_stage = self.env['hr.recruitment.stage'].browse(vals.get('stage_id')) if vals.get('stage_id') else None
        
        # Jalankan proses write asli
        res = super(HrApplicant, self).write(vals)

        # Lakukan pengecekan SETELAH data tersimpan
        for applicant in self:
            # Jika stage baru adalah "Hired" dan batch sudah dipilih
            if new_stage and new_stage.hired_stage and applicant.batch_id:
                # Panggil method untuk membuat participant (logikanya sama seperti di wizard)
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