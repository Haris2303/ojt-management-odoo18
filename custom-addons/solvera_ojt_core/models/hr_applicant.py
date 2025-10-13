# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def action_open_enroll_wizard(self):
        """
        This method is called by the 'Enroll to OJT' button.
        It finds and returns the server action to open the wizard.
        """
        # Pastikan nama modul dan ID action sudah benar
        action = self.env['ir.actions.server']._for_xml_id('solvera_ojt_core.action_hr_applicant_enroll_wizard_server')
        action['context'] = {'active_ids': self.ids}
        return action