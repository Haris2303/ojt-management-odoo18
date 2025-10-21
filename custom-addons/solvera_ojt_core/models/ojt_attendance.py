# -*- coding: utf-8 -*-
from odoo import models, fields, api

class OjtAttendance(models.Model):
    _name = 'ojt.attendance'
    _description = 'OJT Participant Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    event_link_id = fields.Many2one(
        'ojt.event.link', 
        string='Session', 
        required=True, 
        ondelete='cascade'
    )
    participant_id = fields.Many2one(
        'ojt.participant', 
        string='Participant', 
        required=True, 
        ondelete='cascade'
    )
    batch_id = fields.Many2one(
        'ojt.batch', string='OJT Batch', 
        related='event_link_id.batch_id', store=True)
    event_id = fields.Many2one(
        'event.event', string='Event', 
        related='event_link_id.event_id', store=True)
    
    check_in = fields.Datetime(string='Check-in Time', tracking=True)
    check_out = fields.Datetime(string='Check-out Time', tracking=True)
    
    presence = fields.Selection([
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent')
    ], string='Presence Status', default='present', tracking=True)
    
    method = fields.Selection([
        ('qr', 'QR Scan'),
        ('online', 'Online Join'),
        ('manual', 'Manual')
    ], string='Method', default='manual')
    
    duration_minutes = fields.Float(string='Duration (minutes)', compute='_compute_duration')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('participant_event_link_uniq', 'unique(participant_id, event_link_id)', 
        'An attendance record for this participant and session already exists.')
    ]

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out > rec.check_in:
                duration = rec.check_out - rec.check_in
                rec.duration_minutes = duration.total_seconds() / 60.0
            else:
                rec.duration_minutes = 0.0

    @api.constrains('participant_id', 'event_link_id')
    def _check_unique_attendance(self):
        for rec in self:
            if self.search_count([
                ('participant_id', '=', rec.participant_id.id),
                ('event_link_id', '=', rec.event_link_id.id),
                ('id', '!=', rec.id)
            ]) > 0:
                raise models.ValidationError("Peserta ini sudah tercatat absensinya untuk sesi ini.")