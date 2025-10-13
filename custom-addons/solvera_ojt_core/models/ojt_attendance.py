# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Cek presensi otomatis

class OjtAttendance(models.Model):
    _name = 'ojt.attendance'
    _description = 'OJT Participant Attendance'

    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, related='event_link_id.batch_id', store=True)
    event_link_id = fields.Many2one('ojt.event.link', string='Session Link', required=True)
    event_id = fields.Many2one('event.event', string='Event', related='event_link_id.event_id', store=True, required=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True)

    available_event_ids = fields.Many2many('event.event', compute='_compute_available_events')
    
    check_in = fields.Datetime(string='Check-in Time')
    check_out = fields.Datetime(string='Check-out Time')
    
    presence = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent')
    ], string='Presence Status', default='present')
    
    method = fields.Selection([
        ('qr', 'QR Scan'),
        ('online', 'Online Join'),
        ('manual', 'Manual')
    ], string='Method', default='online')
    
    duration_minutes = fields.Float(string='Duration (minutes)', compute='_compute_duration')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('participant_event_uniq', 'unique(participant_id, event_id)', 'An attendance record for this participant and event already exists.')
    ]

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                duration = rec.check_out - rec.check_in
                rec.duration_minutes = duration.total_seconds() / 60.0
            else:
                rec.duration_minutes = 0.0
    
    @api.depends('participant_id')
    def _compute_available_events(self):
        for rec in self:
            if rec.participant_id:
                # Ambil semua event_id dari event_link_ids yang ada di batch peserta
                rec.available_event_ids = rec.participant_id.batch_id.event_link_ids.mapped('event_id')
            else:
                rec.available_event_ids = False
