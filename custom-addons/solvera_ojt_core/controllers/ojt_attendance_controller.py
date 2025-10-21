# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from werkzeug.wrappers import Response
from datetime import timedelta
import pytz

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
    
    @http.route(['/my/agenda/join/<int:event_link_id>'], type='http', auth="user", website=True)
    def portal_join_meeting_and_log(self, event_link_id, **kw):
        event_link = request.env['ojt.event.link'].sudo().browse(event_link_id)
        if not event_link.exists():
            return request.redirect('/my/dashboard')
        
        meeting_url = event_link.online_meeting_url
        if not meeting_url:
            return request.redirect(f'/my/agenda/{event_link.id}')
        
        current_time = fields.Datetime.now()
        event_start_time = event_link.date_start
        
        # Beri masa tenggang 10 menit sebelum sesi boleh diakses
        grace_period_start = event_start_time - timedelta(minutes=10)

        if current_time < grace_period_start:
            start_time_str = event_start_time.astimezone(request.env.user.tz and 
                                                        pytz.timezone(request.env.user.tz) or 
                                                        pytz.utc).strftime('%H:%M pada %d-%m-%Y')
            
            feedback_message = (
                f"Sesi '{event_link.title}' belum dimulai. "
                f"Anda dapat bergabung 10 menit sebelum sesi dimulai. "
                f"Jadwal sesi adalah pukul {start_time_str}."
            )
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {
                'feedback': feedback_message
            })

        user_partner = request.env.user.partner_id
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', user_partner.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.redirect(meeting_url)

        existing_attendance = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id),
            ('event_link_id', '=', event_link.id)
        ], limit=1)

        obj_attendance = {
            'participant_id': participant.id,
            'event_link_id': event_link.id,
            'batch_id': event_link.batch_id.id,
            'event_id': event_link.event_id.id,
            'check_in': current_time,
            'presence': 'present',
            'method': 'online',
        }

        if not existing_attendance:
            late_threshold_time = event_start_time + timedelta(minutes=10)
            
            if current_time > late_threshold_time:
                obj_attendance['presence'] = 'late'

            request.env['ojt.attendance'].sudo().create(obj_attendance)

        cleaned_url = meeting_url.strip() 

        return Response(status=303, headers={'Location': cleaned_url})