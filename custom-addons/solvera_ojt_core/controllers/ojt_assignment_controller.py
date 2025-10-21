# -*- coding: utf-8 -*-
import uuid
import base64
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtAssignmentController(CustomerPortal):

    @http.route(['/my/assignment/<int:assignment_id>'], 
                type='http', auth="user", website=True)
    def portal_my_assignment_detail(self, assignment_id, **kw):
        assignment = request.env['ojt.assignment'].browse(assignment_id)
        
        if not assignment.exists():
            return request.redirect('/my/dashboard')
            
        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', assignment.batch_id.id),
            ('state', 'in', ['active', 'completed'])
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
    
    @http.route(['/my/assignment/submit'], 
                type='http', auth="user", methods=['POST'], website=True)
    def portal_my_assignment_submit(self, **post):
        assignment_id = int(post.get('assignment_id'))
        assignment = request.env['ojt.assignment'].browse(assignment_id)
        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', assignment.batch_id.id),
            ('state', 'in', ['active', 'completed'])
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