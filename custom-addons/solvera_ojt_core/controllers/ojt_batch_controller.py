# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtBatchController(CustomerPortal):

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

        certificate_data = request.env['ojt.certificate'].sudo().search([
            ('participant_id', '=', participant_to_show.id),
            ('state', '=', 'issued')
        ], limit=1)

        values = {
            'participant': participant_to_show,
            'progress_data': progress_data,
            'assignments': all_assignments,
            'agenda_items': agenda_items,
            'survey_data': survey_data,
            'certificate_data': certificate_data,
            'page_name': 'dashboard',
        }
        return request.render("solvera_ojt_core.portal_participant_dashboard", values)