# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtAttendanceController(CustomerPortal):

    @http.route(['/ojt/attend/<string:access_token>'], type='http', auth="user", website=True)
    def ojt_qr_checkin(self, access_token, **kw):
        template = "solvera_ojt_core.portal_template_qr_feedback"

        event_link = request.env['ojt.event.link'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)
        user_partner = request.env.user.partner_id

        if not event_link.exists():
            return request.render(template, {
                'feedback': 'Error: Sesi tidak ditemukan.'
            })
        
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', user_partner.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.render(template, {
                'feedback': 'Maaf, Anda tidak terdaftar sebagai peserta di sesi ini.'
            })

        existing_attendance = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id),
            ('event_link_id', '=', event_link.id)
        ])

        if existing_attendance:
            return request.render(template, {
                'feedback': f'Terima kasih {user_partner.name}, Anda sudah tercatat hadir pada sesi ini.'
            })

        request.env['ojt.attendance'].sudo().create({
            'participant_id': participant.id,
            'event_link_id': event_link.id,
            'batch_id': event_link.batch_id.id,
            'event_id': event_link.event_id.id,
            'check_in': fields.Datetime.now(),
            'presence': 'present',
            'method': 'qr',
        })

        feedback_message = f'Absensi berhasil! Selamat datang, {user_partner.name}.'
        return request.render(template, {
            'feedback': feedback_message
        })