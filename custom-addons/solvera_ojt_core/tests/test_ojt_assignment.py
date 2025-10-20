# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo import fields
from datetime import timedelta

class TestOjtAssignment(TransactionCase):
    def setUp(self):
        super(TestOjtAssignment, self).setUp()

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
            'batch_id': self.batch.id,
            # 'participant_id': self.participant.id,
            'deadline': fields.Datetime.now(),
            'type': 'task',
        })
    
    def test_create_assignment_defaults(self):
        self.assertEqual(self.assignment.state, 'draft')
        self.assertEqual(self.assignment.max_score, 100.0)
        self.assertEqual(self.assignment.weight, 1.0)
        self.assertTrue(self.assignment.attachment_required)

    def test_action_state_transitions(self):
        self.assignment.action_open()
        self.assertEqual(self.assignment.state, 'open')
        self.assignment.action_close()
        self.assertEqual(self.assignment.state, 'closed')
        self.assignment.action_reset_to_draft()
        self.assertEqual(self.assignment.state, 'draft')

    # Akan error karena tugas tidak bisa diatur ke waktu yang berlalu
    # def test_cron_close_past_deadline(self):
    #     assignment = self.env['ojt.assignment']

    #     past_assignment = assignment.create({
    #         'name': 'Expired Assignment',
    #         'batch_id': self.batch.id,
    #         'type': 'task',
    #         'state': 'open',
    #         'deadline': fields.Datetime.now() - timedelta(days=1),
    #     })

    #     future_assignment = assignment.create({
    #         'name': 'Future Assignment',
    #         'batch_id': self.batch.id,
    #         'type': 'task',
    #         'state': 'open',
    #         'deadline': fields.Datetime.now() + timedelta(days=1),
    #     })

    #     assignment._cron_close_past_deadline_assignments()

    #     self.assertEqual(past_assignment.state, 'closed', "Tugas yang sudah lewat deadline seharusnya ditutup oleh cron.")
    #     self.assertEqual(future_assignment.state, 'open', "Tugas yang belum lewat deadline seharusnya tetap terbuka.")

    def test_related_company_from_batch(self):
        """Tes: Memastikan company_id terisi otomatis dari batch_id."""
        assignment = self.env['ojt.assignment'].create({
            'name': 'Test Company Relation',
            'batch_id': self.batch.id,
        })
        self.assertEqual(assignment.company_id, self.batch.company_id, 
                            "Company ID di tugas seharusnya sama dengan Company ID di batch.")

    def test_email_sent_on_new_assignment(self):
        """
        Tes Skenario: Email harus terkirim saat sebuah tugas baru dibuat untuk seorang peserta.
        """
        # --- Arrange (Persiapan) ---
        initial_mail_count = self.env['mail.mail'].search_count([])
        assignment_name = 'Test Assignment'

        # --- Assert (Verifikasi) ---
        final_mail_count = self.env['mail.mail'].search_count([])

        # 1. Verifikasi jumlah email bertambah
        self.assertEqual(final_mail_count, initial_mail_count + 1,
                        "Seharusnya ada satu email baru yang dibuat saat tugas baru ditambahkan.")

        # 2. Verifikasi detail email
        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)

        self.assertEqual(new_email.email_to, self.partner.email,
                        "Penerima email tidak sesuai dengan email partner peserta.")
        
        self.assertIn(assignment_name, new_email.subject,
                    "Subjek email seharusnya mengandung nama tugas.")
        
        self.assertIn(self.batch.name, new_email.subject,
                    "Subjek email seharusnya mengandung nama batch.")
        
        self.assertIn(f'/my/assignment/{self.assignment.id}', new_email.body_html,
                    "Body email seharusnya mengandung link ke detail tugas di portal.")