from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtCertificateController(CustomerPortal):

    @http.route(['/my/certificate/download/<int:certificate_id>'], 
                type='http', auth="user", website=True)
    def portal_my_certificate_download(self, certificate_id, **kw):
        certificate = request.env['ojt.certificate'].sudo().browse(certificate_id)
        
        is_owner = certificate.participant_id.partner_id == request.env.user.partner_id

        if not certificate.exists() or not is_owner or certificate.state != 'issued':
            return request.redirect('/my/certificates')
            
        report_action = request.env['ir.actions.report'].sudo().search([
            ('report_name', '=', 'solvera_ojt_core.report_ojt_certificate_document')
        ], limit=1)

        if not report_action:
            return request.render('http_routing.http_error', {
                'status_code': 500, 
                'status_message': 'Certificate report action not found.'
            })

        pdf = report_action._render_qweb_pdf(report_action.report_name, res_ids=[certificate.id])[0]

        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', f'attachment; filename="Certificate-{certificate.name}.pdf"')
        ]
        return request.make_response(pdf, headers=pdf_http_headers)
    
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