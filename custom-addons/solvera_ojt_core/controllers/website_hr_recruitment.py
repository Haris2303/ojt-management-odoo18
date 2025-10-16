# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment

class CustomWebsiteHrRecruitment(WebsiteHrRecruitment):

    @http.route('/jobs/apply/<model("hr.job"):job>', type='http', auth="public", website=True, sitemap=True)
    def jobs_apply(self, job, **post):
        if not request.session.uid:
            return request.redirect('/web/login?redirect=%s' % request.httprequest.full_path)
        
        existing_applicants = request.env['hr.applicant'].sudo().search([])

        response = super(CustomWebsiteHrRecruitment, self).jobs_apply(job, **post)
        
        if response.status_code == 200 and 'thank_you' in getattr(response, 'template', ''):
            
            new_applicant = request.env['hr.applicant'].sudo().search([
                ('id', 'not in', existing_applicants.ids)
            ], order='id desc', limit=1)
            
            if new_applicant and not new_applicant.partner_id:
                # Jika user yang login belum punya partner, tautkan sekarang
                if not request.env.user.partner_id:
                    request.env.user.partner_id = request.env['res.partner'].sudo().create({'name': request.env.user.name, 'email': request.env.user.login})
                new_applicant.sudo().write({'partner_id': request.env.user.partner_id.id})

        return response