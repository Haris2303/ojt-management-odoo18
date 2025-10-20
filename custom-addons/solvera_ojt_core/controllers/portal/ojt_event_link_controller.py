# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class OjtEventLinkController(CustomerPortal):

    @http.route(['/my/agenda/<int:event_link_id>'], type='http', auth="user", website=True)
    def portal_my_agenda_detail(self, event_link_id, **kw):
        event_link = request.env['ojt.event.link'].browse(event_link_id)
        
        if not event_link.exists():
            return request.redirect('/my/dashboard')

        participant = request.env['ojt.participant'].search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('batch_id', '=', event_link.batch_id.id),
            ('state', '=', ['active', 'completed'])
        ], limit=1)

        if not participant:
            return request.redirect('/my/dashboard')

        values = {
            'event_link': event_link,
            'event': event_link.event_id,
            'page_name': 'agenda_detail',
        }
        return request.render("solvera_ojt_core.portal_ojt_agenda_detail", values)