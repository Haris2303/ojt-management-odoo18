# -*- coding: utf-8 -*-
import base64
import io
import uuid

try:
    import qrcode
except ImportError:
    qrcode = None

from odoo import models, fields, api

class OjtCertificate(models.Model):
    _name = 'ojt.certificate'
    _description = 'OJT Digital Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(
        string='Certificate Title', required=True, tracking=True,
        help="e.g., OJT Business Analyst – Oct 2025")
    
    batch_id = fields.Many2one(
        'ojt.batch', string='OJT Batch', required=True, index=True, tracking=True)
    participant_id = fields.Many2one(
        'ojt.participant', string='Participant', required=True, index=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', 
        related='participant_id.partner_id', store=True)
    
    serial = fields.Char(
        string='Serial Number', required=True, index=True, copy=False, default='/')
    qr_token = fields.Char(
        string='Verification Token', required=True, index=True, copy=False,
        default=lambda self: str(uuid.uuid4()))
    
    issued_date = fields.Date(string='Issue Date', readonly=True, copy=False)
    
    attendance_rate = fields.Float(string='Attendance Rate (%)', readonly=True)
    final_score = fields.Float(string='Final Score', readonly=True)
    
    grade = fields.Selection([
        ('A', 'A'), ('B', 'B'), ('C', 'C')
    ], string='Grade', compute='_compute_grade', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('revoked', 'Revoked')
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Internal Notes')
    qr_code_image = fields.Binary("Verification QR Code", compute='_compute_qr_code')

    access_url = fields.Char('Portal URL', compute='_compute_access_url')

    _sql_constraints = [
        ('serial_uniq', 'unique(serial)', 'The Serial Number must be unique!'),
        ('qr_token_uniq', 'unique(qr_token)', 'The QR Token must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        participant_cache = {}
        
        for vals in vals_list:
            if vals.get('participant_id'):
                participant_id = vals['participant_id']
                
                if participant_id not in participant_cache:
                    participant_cache[participant_id] = self.env['ojt.participant'].browse(participant_id)
                
                participant = participant_cache[participant_id]
                vals.update({
                    'final_score': participant.score_final,
                    'attendance_rate': participant.attendance_rate,
                })

            if vals.get('serial', '/') == '/':
                vals['serial'] = self.env['ir.sequence'].next_by_code('ojt.certificate') or '/'
        
        return super(OjtCertificate, self).create(vals_list)

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
        return self.write({
            'state': 'issued',
            'issued_date': fields.Date.context_today(self),
        })

    @api.depends('qr_token')
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

    def _compute_access_url(self):
        super(OjtCertificate, self)._compute_access_url()
        for certificate in self:
            certificate.access_url = f'/my/certificate/download/{certificate.id}'