# -*- coding: utf-8 -*-
from odoo import models, fields

class Survey(models.Model):
    _inherit = 'survey.survey'

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', 
                                help="Link this survey to a specific OJT batch.")