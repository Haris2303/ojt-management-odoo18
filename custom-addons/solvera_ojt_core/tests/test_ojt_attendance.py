# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestOjtAttendance(TransactionCase):

    def setUp(self):
        super(TestOjtAttendance, self).setUp()
        # Buat batch OJT
        self.batch = self.env['ojt.batch'].create({
            'name': 'Batch 1',
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=30),
            'mode': 'online',
        })

        # Buat partner (peserta)
        self.partner = self.env['res.partner'].create({
            'name': 'John Doe',
            'email': 'john@example.com',
        })

        # Buat participant
        self.participant = self.env['ojt.participant'].create({
            'partner_id': self.partner.id,
            'batch_id': self.batch.id,
        })

        # Buat event
        self.event = self.env['event.event'].create({
            'name': 'OJT Session 1',
            'date_begin': datetime.now(),
            'date_end': datetime.now() + timedelta(hours=2),
        })

        # Buat link antara batch dan event
        self.event_link = self.env['ojt.event.link'].create({
            'event_id': self.event.id,
            'batch_id': self.batch.id,
            'event_id': self.event.id,
            'is_mandatory': True,
        })

    # ---------------------------------------------------------
    # TEST 1 - Record creation
    # ---------------------------------------------------------
    def test_create_attendance(self):
        """Ensure attendance record can be created correctly"""
        attendance = self.env['ojt.attendance'].create({
            'event_link_id': self.event_link.id,
            'participant_id': self.participant.id,
            'check_in': datetime(2025, 1, 1, 9, 0, 0),
            'check_out': datetime(2025, 1, 1, 10, 30, 0),
        })

        self.assertEqual(attendance.event_link_id, self.event_link)
        self.assertEqual(attendance.batch_id, self.batch)
        self.assertEqual(attendance.event_id, self.event)
        self.assertEqual(attendance.duration_minutes, 90.0)
        self.assertEqual(attendance.presence, 'present')
        self.assertEqual(attendance.method, 'manual')

    # ---------------------------------------------------------
    # TEST 2 - Unique constraint
    # ---------------------------------------------------------
    def test_unique_constraint(self):
        """Ensure same participant cannot have duplicate attendance for same event link"""
        self.env['ojt.attendance'].create({
            'event_link_id': self.event_link.id,
            'participant_id': self.participant.id,
        })

        with self.assertRaises(Exception):
            self.env['ojt.attendance'].create({
                'event_link_id': self.event_link.id,
                'participant_id': self.participant.id,
            })

    # ---------------------------------------------------------
    # TEST 3 - Duration compute
    # ---------------------------------------------------------
    def test_compute_duration(self):
        """Ensure duration is computed correctly"""
        attendance = self.env['ojt.attendance'].create({
            'event_link_id': self.event_link.id,
            'participant_id': self.participant.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 9, 30, 0),
        })
        self.assertEqual(attendance.duration_minutes, 90.0)

        # If check_out < check_in, duration should be 0
        attendance.write({
            'check_in': datetime(2025, 1, 1, 10, 0, 0),
            'check_out': datetime(2025, 1, 1, 9, 0, 0),
        })
        self.assertEqual(attendance.duration_minutes, 0.0)

    # ---------------------------------------------------------
    # TEST 4 - Cascade delete
    # ---------------------------------------------------------
    def test_cascade_delete(self):
        """Ensure attendance deleted when event link or participant deleted"""
        attendance = self.env['ojt.attendance'].create({
            'event_link_id': self.event_link.id,
            'participant_id': self.participant.id,
        })
        self.assertTrue(attendance.exists())

        # Deleting event_link should delete attendance
        self.event_link.unlink()
        self.assertFalse(attendance.exists())

    # ---------------------------------------------------------
    # TEST 5 - Field defaults and presence/method
    # ---------------------------------------------------------
    def test_defaults(self):
        """Ensure default presence and method are set properly"""
        attendance = self.env['ojt.attendance'].create({
            'event_link_id': self.event_link.id,
            'participant_id': self.participant.id,
        })
        self.assertEqual(attendance.presence, 'present')
        self.assertEqual(attendance.method, 'manual')

    def test_duplicate_attendance_not_allowed(self):
        self.env['ojt.attendance'].create({
            'participant_id': self.participant.id,
            'event_link_id': self.event_link.id,
        })
        with self.assertRaises(Exception):
            self.env['ojt.attendance'].create({
                'participant_id': self.participant.id,
                'event_link_id': self.event_link.id,
            })