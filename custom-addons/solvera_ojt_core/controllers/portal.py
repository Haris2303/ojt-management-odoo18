# -*- coding: utf-8 -*-
import uuid
# import werkzeug
import base64
from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        # Jalankan method asli untuk mendapatkan nilai-nilai standar (seperti Sales Order, dll.)
        values = super(OjtCustomerPortal, self)._prepare_home_portal_values(counters)
        
        # --- LOGIKA BARU DIMULAI DI SINI ---
        
        # Hitung jumlah OJT Participant (sudah ada)
        participant_count = request.env['ojt.participant'].search_count([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', '=', 'active')
        ])
        
        # Hitung jumlah Lamaran Pekerjaan milik user yang login
        # Ini akan otomatis difilter oleh Record Rule yang sudah kita buat
        application_count = request.env['hr.applicant'].search_count([])
        
        # Tambahkan hasil hitungan ke dictionary 'values'
        values.update({
            'ojt_count': participant_count,
            'application_count': application_count,
        })
        return values

    # ==========================================================
    # METHOD INI DIPERBAIKI UNTUK MULTI-BATCH
    # ==========================================================
    @http.route(['/my/ojt'], type='http', auth="user", website=True)
    def portal_my_ojt_agenda(self, participant_id=None, **kw):
        user_partner = request.env.user.partner_id
        participants = request.env['ojt.participant'].search([
            ('partner_id', '=', user_partner.id),
            ('state', '=', 'active')
        ])

        if not participants:
            return request.redirect('/my')

        if participant_id:
            participant_to_show = participants.filtered(lambda p: p.id == int(participant_id))
        elif len(participants) == 1:
            participant_to_show = participants
        else:
            # Jika punya banyak batch, arahkan ke dashboard untuk memilih
            return request.redirect('/my/dashboard')
            
        if not participant_to_show:
            return request.redirect('/my')

        values = {
            'participant': participant_to_show,
            'agenda_items': participant_to_show.batch_id.event_link_ids,
            'page_name': 'ojt_agenda',
        }
        return request.render("solvera_ojt_core.portal_template_ojt_agenda", values)
    
    # ==========================================================
    # METHOD INI TIDAK PERLU DIUBAH, LOGIKANYA SUDAH BENAR
    # ==========================================================
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
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {'feedback': 'Maaf, Anda tidak terdaftar sebagai peserta di sesi ini.'})

        existing_attendance = request.env['ojt.attendance'].sudo().search([
            ('participant_id', '=', participant.id),
            ('event_link_id', '=', event_link.id)
        ])

        if existing_attendance:
            return request.render("solvera_ojt_core.portal_template_qr_feedback", {'feedback': f'Terima kasih {user_partner.name}, Anda sudah tercatat hadir pada sesi ini.'})

        request.env['ojt.attendance'].sudo().create({
            'participant_id': participant.id,
            'event_link_id': event_link.id,
            'batch_id': event_link.batch_id.id,
            'event_id': event_link.event_id.id,
            # 'company_id': event_link.event_id.company_id.id, 
            'check_in': fields.Datetime.now(),
            'presence': 'present',
            'method': 'qr',
        })

        feedback_message = f'Absensi berhasil! Selamat datang, {user_partner.name}.'
        return request.render("solvera_ojt_core.portal_template_qr_feedback", {'feedback': feedback_message})
    
    # ==========================================================
    # METHOD INI DIPERBAIKI UNTUK MULTI-BATCH
    # ==========================================================
    @http.route(['/my/dashboard'], type='http', auth="user", website=True)
    def portal_my_dashboard(self, participant_id=None, **kw):
        user_partner = request.env.user.partner_id
        
        # Cari SEMUA record participant yang aktif (hapus limit=1)
        participants = request.env['ojt.participant'].search([
            ('partner_id', '=', user_partner.id),
            ('state', '=', 'active')
        ])

        if not participants:
            # Jika tidak terdaftar sama sekali, arahkan ke home
            return request.redirect('/my')

        # Logika untuk memilih participant yang akan ditampilkan
        if participant_id:
            # Jika ID spesifik diberikan (dari halaman pemilihan), gunakan itu
            participant_to_show = participants.filtered(lambda p: p.id == int(participant_id))
        elif len(participants) == 1:
            # Jika hanya ada satu, langsung gunakan itu
            participant_to_show = participants
        else:
            # Jika ada LEBIH DARI SATU, tampilkan halaman pemilihan
            return request.render("solvera_ojt_core.portal_participant_batch_selection", {
                'participants': participants,
                'page_name': 'batch_selection'
            })

        if not participant_to_show:
            # Pengaman jika participant_id yang diberikan tidak valid
            return request.redirect('/my/dashboard')

        # -- Sisa dari kode dashboard tetap sama, menggunakan 'participant_to_show' --
        
        assignment_submitted = request.env['ojt.assignment.submit'].search_count([
            ('participant_id', '=', participant_to_show.batch_id.id)
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

        values = {
            'participant': participant_to_show,
            'progress_data': progress_data,
            'assignments': all_assignments,
            'agenda_items': agenda_items,
            'page_name': 'dashboard',
        }
        return request.render("solvera_ojt_core.portal_participant_dashboard", values)

    @http.route(['/my/agenda/<int:event_link_id>'], type='http', auth="user", website=True)
    def portal_my_agenda_detail(self, event_link_id, **kw):
        # 1. Ambil record event_link yang diminta
        event_link = request.env['ojt.event.link'].browse(event_link_id)
        
        # 2. VALIDASI PERTAMA: Pastikan event_link ditemukan SEBELUM mengakses field-nya
        if not event_link.exists():
            # Jika agenda tidak ada, langsung kembali ke dashboard
            return request.redirect('/my/dashboard')

        # 3. VALIDASI KEDUA (Keamanan): Sekarang baru kita pastikan user boleh melihatnya
        # Karena sudah pasti event_link ada, kita aman mengakses event_link.batch_id.id
        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', 'active')
        ], limit=1)

        if not participant:
            # Jika user tidak berhak, kembalikan juga ke dashboard
            return request.redirect('/my/dashboard')

        # 4. Jika semua validasi lolos, kirim data ke template
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

        # --- PERUBAHAN UTAMA DI SINI ---
        # Siapkan daftar lampiran dengan URL yang sudah jadi
        attachment_data = []
        if submission:
            for attachment in submission.attachment_ids:
                # Gunakan sudo() untuk membaca access_token yang terproteksi
                token = attachment.sudo().access_token
                attachment_data.append({
                    'name': attachment.name,
                    'url': f'/web/content/{attachment.id}?access_token={token}'
                })
        # --- AKHIR PERUBAHAN ---

        values = {
            'assignment': assignment,
            'participant': participant,
            'submission': submission,
            'attachment_data': attachment_data, # Kirim data lampiran yang sudah diproses
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
                # 1. Buat token unik secara manual
                token = str(uuid.uuid4())

                # 2. Simpan token langsung saat membuat attachment
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': ufile.filename,
                    'datas': base64.b64encode(ufile.read()),
                    'res_model': 'ojt.assignment.submit',
                    'res_id': new_submission.id,
                    'access_token': token, # <-- Token dimasukkan di sini
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

        # --- PERBAIKAN UTAMA DI SINI ---
        # Memanggil report action dengan cara yang benar
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
        # Cari semua batch yang statusnya sedang rekrutmen atau sedang berjalan
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
            # Cari sertifikat berdasarkan token unik. Gunakan sudo() karena ini halaman publik.
            certificate = request.env['ojt.certificate'].sudo().search([
                ('qr_token', '=', token),
                ('state', '=', 'issued') # Hanya tampilkan sertifikat yang sudah "Issued"
            ], limit=1)

        values = {
            'certificate': certificate,
            'token': token,
        }
        return request.render("solvera_ojt_core.ojt_certificate_verification_page", values)

    @http.route(['/my/applications'], type='http', auth="user", website=True)
    def portal_my_applications(self, **kw):
        # Cari semua lamaran yang terhubung dengan partner pengguna yang login
        # Record Rule yang sudah kita buat akan otomatis memfilter ini
        applications = request.env['hr.applicant'].search([])
        
        values = {
            'applications': applications,
            'page_name': 'applications',
        }
        return request.render("solvera_ojt_core.portal_my_applications_list", values)