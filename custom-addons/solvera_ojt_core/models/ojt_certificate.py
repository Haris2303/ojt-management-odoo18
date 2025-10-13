# -*- coding: utf-8 -*-
import base64
import io
try:
    import qrcode
except ImportError:
    qrcode = None
import uuid
from odoo import models, fields, api

# Bagian ini harus di bedah

class OjtCertificate(models.Model):
    _name = 'ojt.certificate'
    _description = 'OJT Digital Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Certificate Title', required=True, help="e.g., OJT Business Analyst – Oct 2025")
    
    batch_id = fields.Many2one('ojt.batch', string='OJT Batch', required=True, index=True)
    participant_id = fields.Many2one('ojt.participant', string='Participant', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='participant_id.partner_id', store=True)
    
    # Ada kode unik dari serial untuk sequence !!!!!!!
    serial = fields.Char(string='Serial Number', required=True, unique=True, index=True, copy=False, default='/')
    qr_token = fields.Char(string='Verification Token', required=True, unique=True, index=True, copy=False, default=lambda self: str(uuid.uuid4()))
    
    issued_on = fields.Date(string='Issued On', default=fields.Date.today)
    
    # Store the values at the time of issuance
    attendance_rate = fields.Float(string='Attendance Rate (%)', store=True)
    final_score = fields.Float(string='Final Score', store=True)
    
    grade = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')
    ], string='Grade', compute='_compute_grade', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('revoked', 'Revoked')
    ], string='Status', default='draft', track_visibility='onchange')
    
    notes = fields.Text(string='Internal Notes')

    qr_code_image = fields.Binary("Verification QR Code", compute='_compute_qr_code')

    @api.model
    def create(self, vals):
        # Ambil data dari participant dan sisipkan ke vals sebelum record dibuat
        if vals.get('participant_id'):
            participant = self.env['ojt.participant'].browse(vals['participant_id'])
            vals['final_score'] = participant.score_final
            vals['attendance_rate'] = participant.attendance_rate
        # --- AKHIR LOGIKA BARU ---

        # Lanjutkan dengan logic sequence number yang sudah ada
        if vals.get('serial', '/') == '/':
            vals['serial'] = self.env['ir.sequence'].next_by_code('ojt.certificate') or '/'
        
        return super(OjtCertificate, self).create(vals)

    @api.depends('final_score')
    def _compute_grade(self):
        for cert in self:
            if cert.final_score >= 85:
                cert.grade = 'A'
            elif cert.final_score >= 75:
                cert.grade = 'B'
            else:
                cert.grade = 'C'

    def action_issue(self):
        """Changes the certificate state to 'Issued'."""
        self.write({
            'state': 'issued',
            'issued_on': fields.Date.context_today(self)
        })
        return True
    
    def _compute_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if qrcode and rec.qr_token:
                qr_url = f'{base_url}/ojt/cert/verify?token={rec.qr_token}'
                img = qrcode.make(qr_url)
                temp = io.BytesIO()
                img.save(temp, format="PNG")
                rec.qr_code_image = base64.b64encode(temp.getvalue())
            else:
                rec.qr_code_image = False
