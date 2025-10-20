# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo import fields

class TestOjtAssignmentSubmit(TransactionCase):
    def setUp(self):
        super(TestOjtAssignmentSubmit, self).setUp()
        # Data dasar
        self.partner = self.env['res.partner'].create({
            'name': 'Budi Tester', 'email': 'budi.test@example.com'
        })
        self.batch = self.env['ojt.batch'].create({
            'name': 'Test Batch', 'start_date': fields.Date.today(), 'end_date': fields.Date.today()
        })
        self.participant = self.env['ojt.participant'].create({
            'partner_id': self.partner.id, 'batch_id': self.batch.id
        })
        self.assignment = self.env['ojt.assignment'].create({
            'name': 'Tugas Final', 'batch_id': self.batch.id
        })

    def test_email_sent_on_submission_scored(self):
        """
        Tes Skenario: Email harus terkirim saat submission ditandai 'Scored'.
        """
        # --- Arrange ---
        submission = self.env['ojt.assignment.submit'].create({
            'assignment_id': self.assignment.id,
            'participant_id': self.participant.id,
            'state': 'submitted', # Awalnya 'submitted'
            'score': 95.0, # Skor sudah diisi oleh mentor
            'feedback': '<p>Kerja bagus!</p>'
        })
        initial_mail_count = self.env['mail.mail'].search_count([])

        # --- Act ---
        # Mentor menekan tombol "Mark as Scored"
        submission.action_mark_as_scored()

        # --- Assert ---
        final_mail_count = self.env['mail.mail'].search_count([])
        self.assertEqual(final_mail_count, initial_mail_count + 1, "Seharusnya ada 1 email baru yang dibuat.")

        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(new_email.email_to, self.partner.email)
        self.assertIn(self.assignment.name, new_email.subject)
        self.assertIn('95', new_email.body_html) # Pastikan skor ada di email
        self.assertIn('Kerja bagus!', new_email.body_html) # Pastikan feedback ada di email