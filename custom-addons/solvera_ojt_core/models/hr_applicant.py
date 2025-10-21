# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    batch_id = fields.Many2one('ojt.batch', string='Target OJT Batch',
                                domain="[('state', 'in', ['draft', 'recruit'])]")
    
    portal_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'Pending'),
        ('shortlisted', 'In Process'),
        ('accepted', 'Accepted'),
        ('rejected', 'Not Retained'),
    ], string="Portal Status", compute='_compute_portal_status')

    def action_open_enroll_wizard(self):
        self.ensure_one()
        
        if self.stage_id.name.lower() != 'new':
            raise UserError("You can only enroll an applicant from a 'New' stage.")

        action = self.env['ir.actions.act_window']._for_xml_id('solvera_ojt_core.action_hr_applicant_enroll_wizard_window')
        action['context'] = {'default_applicant_ids': self.ids}
        return action

    def write(self, vals):
        if 'stage_id' in vals:
            if not self.env.context.get('enroll_from_wizard'):
                new_stage = self.env['hr.recruitment.stage'].browse(vals.get('stage_id'))
                if new_stage and 'ojt' in new_stage.name.lower():
                    raise ValidationError("Anda tidak dapat memindahkan pelamar ke stage 'OJT' secara manual. Gunakan tombol 'Enroll to OJT' untuk melanjutkan.")

        res = super(HrApplicant, self).write(vals)

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
        for applicant in self:
            if applicant.stage_id.hired_stage:
                applicant.portal_status = 'accepted'
            elif applicant.stage_id.sequence == 0:
                applicant.portal_status = 'new'
            elif applicant.stage_id.sequence == 1:
                applicant.portal_status = 'pending'
            elif 'refuse' in applicant.stage_id.name.lower() or 'rejected' in applicant.stage_id.name.lower():
                applicant.portal_status = 'rejected'
            else:
                applicant.portal_status = 'shortlisted'