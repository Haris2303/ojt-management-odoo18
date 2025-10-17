# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo import fields
from datetime import timedelta

class TestOjtAssignment(TransactionCase):
    def setUp(self):
        super(TestOjtAssignment, self).setUp()

         # Create company (jika company_id diperlukan di batch)
        self.company = self.env['res.company'].create({
            'name': 'Test Company'
        })

        # Create batch
        self.batch = self.env['ojt.batch'].create({
            'name': 'Batch Alpha',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'company_id': self.company.id,
        })

        # Create partner
        self.partner = self.env['res.partner'].create({
            'name': 'John Doe',
            'email': 'john@example.com',
        })

        # Create participant
        self.participant = self.env['ojt.participant'].create({
            'name': 'John Doe',
            'partner_id': self.partner.id,
            'batch_id': self.batch.id,
            'company_id': self.company.id,
        })

        # Create assignment
        self.assignment = self.env['ojt.assignment'].create({
            'name': 'Test Assignment',
            'participant_id': self.participant.id,
            'deadline': fields.Datetime.now(),
            'type': 'task',
        })
    
    def test_create_assignment_defaults(self):
        assignment = self.env['ojt.assignment'].create({
            'name': 'Tugas Pertama',
            'type': 'task',
        })
        self.assertEqual(assignment.state, 'draft')
        self.assertEqual(assignment.max_score, 100.0)
        self.assertEqual(assignment.weight, 1.0)
        self.assertTrue(assignment.attachment_required)

    def test_action_state_transitions(self):
        assignment = self.env['ojt.assignment'].create({'name': 'Test State', 'type': 'task'})
        assignment.action_open()
        self.assertEqual(assignment.state, 'open')
        assignment.action_close()
        self.assertEqual(assignment.state, 'closed')
        assignment.action_reset_to_draft()
        self.assertEqual(assignment.state, 'draft')

    def test_cron_close_past_deadline(self):
        assignment = self.env['ojt.assignment']

        past_assignment = assignment.create({
            'name': 'Expired Assignment',
            'type': 'task',
            'state': 'open',
            'deadline': fields.Datetime.now() - timedelta(days=1),
        })

        future_assignment = assignment.create({
            'name': 'Future Assignment',
            'type': 'task',
            'state': 'open',
            'deadline': fields.Datetime.now() + timedelta(days=1),
        })

        assignment._cron_close_past_deadline_assignments()

        self.assertEqual(past_assignment.state, 'closed')
        self.assertEqual(future_assignment.state, 'open')

    def test_related_fields_from_participant(self):
        participant = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner.id,
        })
        assignment = self.env['ojt.assignment'].create({
            'name': 'Relasi Test',
            'participant_id': participant.id,
            'type': 'task',
        })
        self.assertEqual(assignment.batch_id.id, participant.batch_id.id)
        self.assertEqual(assignment.company_id.id, participant.company_id.id)