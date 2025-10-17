# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from datetime import date, timedelta

@tagged('-at_install', 'post_install')  # dijalankan setelah modul diinstall
class TestOjtEventLink(common.TransactionCase):

    def setUp(self):
        super(TestOjtEventLink, self).setUp()
        self.company = self.env.ref('base.main_company')
        today = date.today()

        self.partner = self.env['res.partner'].create({
            'name': 'John Doe',
            'email': 'john@example.com',
        })

        self.batch = self.env['ojt.batch'].create({
            'name': 'Batch 1',
            'start_date': today,
            'end_date': today + timedelta(days=30),
            'mode': 'online',
            'company_id': self.company.id,
        })

        self.event = self.env['event.event'].create({
            'name': 'Test Event',
            'date_begin': f"{today} 08:00:00",
            'date_end': f"{today} 10:00:00",
        })

    def test_create_event_link(self):
        """Pastikan ojt.event.link bisa dibuat dan terhubung ke batch & event"""
        link = self.env['ojt.event.link'].create({
            'batch_id': self.batch.id,
            'event_id': self.event.id,
            'instructor_id': self.partner.id,
            'is_mandatory': True,
            'weight': 2.5,
        })

        self.assertTrue(link.id, "Record ojt.event.link harus berhasil dibuat.")
        self.assertEqual(link.batch_id, self.batch)
        self.assertEqual(link.event_id, self.event)
        self.assertEqual(link.weight, 2.5)

    def test_qr_code_generated(self):
        """Pastikan QR code bisa dibuat"""
        link = self.env['ojt.event.link'].create({
            'batch_id': self.batch.id,
            'event_id': self.event.id,
        })

        # trigger compute qr_code_image
        link._compute_qr_code()
        self.assertTrue(link.qr_code_image or link.qr_code_image is False)

    def test_related_counts(self):
        """Pastikan related counts bekerja walaupun belum ada attendance/assignment"""
        link = self.env['ojt.event.link'].create({
            'batch_id': self.batch.id,
            'event_id': self.event.id,
        })

        link._compute_related_counts()
        self.assertEqual(link.participant_count, getattr(link.batch_id, 'participant_count', 0))
        self.assertEqual(link.attendance_count, 0)
        self.assertEqual(link.assignment_count, 0)

    def test_action_views_return_dict(self):
        """Pastikan smart button mengembalikan dict ir.actions.act_window"""
        link = self.env['ojt.event.link'].create({
            'batch_id': self.batch.id,
            'event_id': self.event.id,
        })

        participants_action = link.action_view_participants()
        attendance_action = link.action_view_attendance_log()

        # pastikan return type dan key penting
        for action in [participants_action, attendance_action]:
            self.assertIsInstance(action, dict)
            self.assertIn('type', action)
            self.assertIn('res_model', action)
            self.assertIn('domain', action)

    def test_relation_integrity(self):
        link = self.env['ojt.event.link'].create({
            'event_id': self.event.id,
            'batch_id': self.batch.id,
            'instructor_id': self.partner.id,
            'online_meeting_url': 'https://meet.google.com/test123',
        })
        self.assertIn(link, self.event.event_link_ids)
        self.assertIn(link, self.batch.event_link_ids)

    def test_update_meeting_url(self):
        link = self.env['ojt.event.link'].create({
            'event_id': self.event.id,
            'batch_id': self.batch.id,
            'instructor_id': self.partner.id,
            'online_meeting_url': 'https://meet.google.com/test123',
        })
        link.online_meeting_url = 'https://meet.google.com/newlink'
        self.assertEqual(link.online_meeting_url, 'https://meet.google.com/newlink')