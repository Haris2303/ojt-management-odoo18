# -*- coding: utf-8 -*-
import uuid
import base64
import werkzeug
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(OjtCustomerPortal, self)._prepare_home_portal_values(counters)
        
        participant_count = request.env['ojt.participant'].search_count([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', 'in', ['active', 'completed'])
        ])
        
        application_count = request.env['hr.applicant'].search_count([])
        
        values.update({
            'ojt_count': participant_count,
            'application_count': application_count,
        })
        return values
    
    @http.route(['/ojt/attend/<int:event_link_id>'], type='http', auth="user", website=True)
    def ojt_qr_checkin(self, event_link_id, **kw):
        event_link = request.env['ojt.event.link'].sudo().browse(event_link_id)
        user_partner = request.env.user.partner_id

        if not event_link.exists():
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {
                        'feedback': 'Error: Sesi tidak ditemukan.'
                    })
        
        participant = request.env['ojt.participant'].sudo().search([
            ('partner_id', '=', user_partner.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {
                    'feedback': 'Maaf, Anda tidak terdaftar sebagai peserta di sesi ini.'
                })

        existing_attendance = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id),
            ('event_link_id', '=', event_link.id)
        ])

        if existing_attendance:
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {
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
        return request.render("solvera_ojt_core.portal_template_qr_feedback", {
                'feedback': feedback_message
            })
    
    @http.route(['/my/dashboard'], type='http', auth="user", website=True)
    def portal_my_dashboard(self, participant_id=None, **kw):
        user_partner = request.env.user.partner_id
        
        participants = request.env['ojt.participant'].search([
            ('partner_id', '=', user_partner.id),
            ('state', 'in', ['active', 'completed'])
        ])

        if not participants:
            return request.redirect('/my')

        if participant_id:
            participant_to_show = participants.filtered(lambda p: p.id == int(participant_id))
        elif len(participants) == 1:
            participant_to_show = participants
        else:
            return request.render("solvera_ojt_core.portal_participant_batch_selection", {
                'participants': participants,
                'page_name': 'batch_selection'
            })

        if not participant_to_show:
            return request.redirect('/my/dashboard')

        assignment_submitted = request.env['ojt.assignment.submit'].search_count([
            ('participant_id', '=', participant_to_show.id)
        ])
        assignment_total = request.env['ojt.assignment'].search_count([
            ('batch_id', '=', participant_to_show.batch_id.id),
            ('state', '!=', 'draft')
        ])
        progress_data = {
            'assignment_completed_count': assignment_submitted,
            'assignment_total_count': assignment_total,
        }

        all_assignments = request.env['ojt.assignment'].search([
            ('batch_id', '=', participant_to_show.batch_id.id),
            ('state', '!=', 'draft')
        ])
        
        agenda_items = participant_to_show.batch_id.event_link_ids.sorted(key=lambda r: r.event_id.date_begin)

        surveys_to_check = participant_to_show.batch_id.sudo().survey_id

        survey_data = []
        if surveys_to_check:
            user_inputs = request.env['survey.user_input'].sudo().search([
                ('partner_id', '=', user_partner.id),
                ('survey_id', 'in', surveys_to_check.ids),
                ('state', '=', 'done')
            ])
            completed_survey_ids = user_inputs.mapped('survey_id').ids

            for survey in surveys_to_check:
                survey_data.append({
                    'survey': survey,
                    'is_done': survey.id in completed_survey_ids,
                })

        values = {
            'participant': participant_to_show,
            'progress_data': progress_data,
            'assignments': all_assignments,
            'agenda_items': agenda_items,
            'survey_data': survey_data,
            'page_name': 'dashboard',
        }
        return request.render("solvera_ojt_core.portal_participant_dashboard", values)

    @http.route(['/my/agenda/<int:event_link_id>'], type='http', auth="user", website=True)
    def portal_my_agenda_detail(self, event_link_id, **kw):
        event_link = request.env['ojt.event.link'].browse(event_link_id)
        
        if not event_link.exists():
            return request.redirect('/my/dashboard')

        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.redirect('/my/dashboard')

        values = {
            'event_link': event_link,
            'event': event_link.event_id,
            'page_name': 'agenda_detail',
        }
        return request.render("solvera_ojt_core.portal_ojt_agenda_detail", values)
    
    @http.route(['/my/assignment/<int:assignment_id>'], type='http', auth="user", website=True)
    def portal_my_assignment_detail(self, assignment_id, **kw):
        assignment = request.env['ojt.assignment'].browse(assignment_id)
        
        if not assignment.exists():
            return request.redirect('/my/dashboard')
            
        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', assignment.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.redirect('/my/dashboard')

        submission = request.env['ojt.assignment.submit'].search([
            ('assignment_id', '=', assignment.id),
            ('participant_id', '=', participant.id)
        ], limit=1)

        attachment_data = []
        if submission:
            for attachment in submission.attachment_ids:
                token = attachment.sudo().access_token
                attachment_data.append({
                    'name': attachment.name,
                    'url': f'/web/content/{attachment.id}?access_token={token}'
                })

        values = {
            'assignment': assignment,
            'participant': participant,
            'submission': submission,
            'attachment_data': attachment_data,
            'page_name': 'assignment_detail',
        }
        return request.render("solvera_ojt_core.portal_assignment_detail", values)
    
    @http.route(['/my/assignment/submit'], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_assignment_submit(self, **post):
        assignment_id = int(post.get('assignment_id'))
        assignment = request.env['ojt.assignment'].browse(assignment_id)
        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', assignment.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            return request.redirect('/my/home')

        new_submission = request.env['ojt.assignment.submit'].create({
            'assignment_id': assignment_id,
            'participant_id': participant.id,
            'url_link': post.get('url_link'),
        })

        attachment_ids = []
        uploaded_files = request.httprequest.files.getlist('attachments')
        for ufile in uploaded_files:
            if ufile.filename:
                token = str(uuid.uuid4())

                attachment = request.env['ir.attachment'].sudo().create({
                    'name': ufile.filename,
                    'datas': base64.b64encode(ufile.read()),
                    'res_model': 'ojt.assignment.submit',
                    'res_id': new_submission.id,
                    'access_token': token,
                })
                attachment_ids.append(attachment.id)

        if attachment_ids:
            new_submission.write({
                'attachment_ids': [(6, 0, attachment_ids)]
            })

        return request.redirect(f'/my/assignment/{assignment_id}')
    
    @http.route(['/my/certificate/download/<int:certificate_id>'], type='http', auth="user", website=True)
    def portal_my_certificate_download(self, certificate_id, **kw):
        certificate = request.env['ojt.certificate'].sudo().browse(certificate_id)
        
        is_owner = certificate.participant_id.partner_id == request.env.user.partner_id

        if not certificate.exists() or not is_owner or certificate.state != 'issued':
            return request.redirect('/my/certificates')
            
        report_action = request.env['ir.actions.report'].sudo().search([
            ('report_name', '=', 'solvera_ojt_core.report_ojt_certificate_document')
        ], limit=1)

        if not report_action:
            return request.render('http_routing.http_error', {'status_code': 500, 'status_message': 'Certificate report action not found.'})

        pdf = report_action._render_qweb_pdf(report_action.report_name, res_ids=[certificate.id])[0]

        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Certificate-{certificate.name}.pdf"')
        ]
        return request.make_response(pdf, headers=pdf_http_headers)
    
    @http.route(['/my/certificates'], type='http', auth="user", website=True)
    def portal_my_certificates(self, **kw):
        participants = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ])
        
        values = {
            'participants': participants,
            'page_name': 'certificates',
        }
        return request.render("solvera_ojt_core.portal_my_certificates", values)
    
    @http.route(['/ojt/programs'], type='http', auth="public", website=True)
    def ojt_program_list(self, **kw):
        active_batches = request.env['ojt.batch'].search([
            ('state', 'in', ['recruit', 'ongoing'])
        ])
        
        values = {
            'batches': active_batches,
        }
        return request.render("solvera_ojt_core.ojt_program_list_template", values)

    @http.route(['/ojt/cert/verify'], type='http', auth="public", website=True)
    def ojt_certificate_verify(self, token=None, **kw):
        certificate = None
        if token:
            certificate = request.env['ojt.certificate'].sudo().search([
                ('qr_token', '=', token),
                ('state', '=', 'issued')
            ], limit=1)

        values = {
            'certificate': certificate,
            'token': token,
        }
        return request.render("solvera_ojt_core.ojt_certificate_verification_page", values)

    @http.route(['/my/applications'], type='http', auth="user", website=True)
    def portal_my_applications(self, **kw):
        applications = request.env['hr.applicant'].search([])
        
        values = {
            'applications': applications,
            'page_name': 'applications',
        }
        return request.render("solvera_ojt_core.portal_my_applications_list", values)