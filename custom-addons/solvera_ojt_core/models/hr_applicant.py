# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Field untuk memilih batch tujuan sebelum applicant diterima
    batch_id = fields.Many2one(
        'ojt.batch', 
        string='Target OJT Batch',
        domain="[('state', 'in', ['draft', 'recruit'])]",
        tracking=True
    )
    
    # Field untuk menampilkan status sederhana di portal
    portal_status = fields.Selection([
        ('pending', 'Pending'),
        ('shortlisted', 'In Process'),
        ('accepted', 'Accepted'),
        ('rejected', 'Not Retained'),
    ], string="Portal Status", compute='_compute_portal_status', store=True)

    @api.depends('stage_id.name', 'stage_id.hired_stage')
    def _compute_portal_status(self):
        """Menerjemahkan stage internal menjadi status yang mudah dipahami di portal."""
        for applicant in self:
            if applicant.stage_id.hired_stage:
                applicant.portal_status = 'accepted'
            elif applicant.stage_id.sequence <= 1: # Stage paling awal dianggap 'pending'
                applicant.portal_status = 'pending'
            # Anda bisa menambahkan logika untuk 'rejected' jika Anda membuat stage khusus
            else: # Semua stage di antaranya dianggap 'In Process'
                applicant.portal_status = 'shortlisted'
    
    def action_open_enroll_wizard(self):
        self.ensure_one()
        
        # Validasi di sisi server
        first_stage = self.env['hr.recruitment.stage'].search([], order='sequence asc', limit=1)
        if self.stage_id != first_stage:
            raise UserError(f"Anda hanya bisa mendaftarkan pelamar dari stage '{first_stage.name}'.")

        # Jika lolos, buka wizard
        action = self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_hr_applicant_enroll_wizard_window')
        action['context'] = {'active_ids': self.ids}
        return action

    def write(self, vals):
        """
        Otomatis membuat OJT Participant saat applicant dipindahkan ke stage 'Hired'.
        """
        # Panggil method write asli terlebih dahulu
        res = super(HrApplicant, self).write(vals)

        # Cek apakah stage diubah ke stage 'Hired'
        if 'stage_id' in vals:
            new_stage = self.env['hr.recruitment.stage'].browse(vals.get('stage_id'))
            if new_stage and new_stage.hired_stage:
                # Loop melalui setiap applicant yang diubah
                for applicant in self:
                    # Pastikan batch sudah dipilih
                    if not applicant.batch_id:
                        raise ValidationError(f"Pilih 'Target OJT Batch' terlebih dahulu untuk pelamar {applicant.name}.")
                    
                    # Panggil wizard untuk membuat participant dan mengirim email
                    # Ini menggunakan kembali logika yang sudah ada di wizard
                    self.env['hr.applicant.enroll.wizard'].create({
                        'applicant_ids': [(4, applicant.id)],
                        'batch_id': applicant.batch_id.id,
                    }).action_enroll()
        return res