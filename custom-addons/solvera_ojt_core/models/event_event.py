# -*- coding: utf-8 -*-
from odoo import models, fields

class EventEvent(models.Model):
    _inherit = 'event.event'

    online_meeting_url = fields.Char(string="Online Meeting URL")
    event_link_ids = fields.One2many('ojt.event.link', 'event_id', string='OJT Batch Links')