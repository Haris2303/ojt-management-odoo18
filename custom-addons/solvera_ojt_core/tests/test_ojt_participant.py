# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestOjtParticipant(TransactionCase):
    """
    Kelompok tes untuk memvalidasi logika bisnis dari model ojt.participant.
    """

    def setUp(self, *args, **kwargs):
        """Siapkan data master yang akan digunakan oleh semua tes."""
        super(TestOjtParticipant, self).setUp(*args, **kwargs)

        # Buat data dasar yang sering digunakan
        self.batch = self.env['ojt.batch'].create({
            'name': 'OJT Backend Developer 2025',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })
        self.partner = self.env['res.partner'].create({'name': 'Budi Santoso'})

    def test_01_compute_name(self):
        """Tes: Format nama peserta harus 'Nama Partner - Nama Batch'."""
        participant = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner.id,
        })
        expected_name = "Budi Santoso - OJT Backend Developer 2025"
        self.assertEqual(participant.name, expected_name, "Format nama peserta tidak sesuai harapan.")

    def test_02_compute_attendance_rate(self):
        """Tes: Perhitungan attendance rate harus akurat dan hanya menghitung sesi wajib."""
        # Buat 2 sesi wajib dan 1 sesi tidak wajib
        event1 = self.env['event.event'].create({'name': 'Sesi Wajib 1'})
        event2 = self.env['event.event'].create({'name': 'Sesi Wajib 2'})
        event3 = self.env['event.event'].create({'name': 'Sesi Opsional'})
        
        link1 = self.env['ojt.event.link'].create({'batch_id': self.batch.id, 'event_id': event1.id, 'is_mandatory': True})
        link2 = self.env['ojt.event.link'].create({'batch_id': self.batch.id, 'event_id': event2.id, 'is_mandatory': True})
        link3 = self.env['ojt.event.link'].create({'batch_id': self.batch.id, 'event_id': event3.id, 'is_mandatory': False})

        participant = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner.id,
        })
        
        # Hadir di 1 sesi wajib (1 dari 2 sesi wajib = 50%)
        self.env['ojt.attendance'].create({'participant_id': participant.id, 'event_link_id': link1.id, 'presence': 'present'})
        participant.invalidate_recordset(['attendance_rate', 'attendance_count'])
        self.assertEqual(participant.attendance_rate, 50.0, "Attendance rate seharusnya 50% setelah 1 sesi wajib.")

        # Hadir di sesi opsional (rate tidak boleh berubah)
        self.env['ojt.attendance'].create({'participant_id': participant.id, 'event_link_id': link3.id, 'presence': 'present'})
        participant.invalidate_recordset(['attendance_rate', 'attendance_count'])
        self.assertEqual(participant.attendance_rate, 50.0, "Rate tidak boleh berubah setelah hadir di sesi opsional.")
        
        # Hadir di sesi wajib kedua (2 dari 2 sesi wajib = 100%)
        self.env['ojt.attendance'].create({'participant_id': participant.id, 'event_link_id': link2.id, 'presence': 'present'})
        participant.invalidate_recordset(['attendance_rate', 'attendance_count'])
        self.assertEqual(participant.attendance_rate, 100.0, "Attendance rate seharusnya 100% setelah 2 sesi wajib.")

    def test_03_compute_scores_weighted_average(self):
        """Tes: Perhitungan score_final dengan bobot harus akurat."""
        
        assignment1 = self.env['ojt.assignment'].create({'name': 'Tugas 1', 'batch_id': self.batch.id, 'max_score': 100.0, 'weight': 2.0})
        assignment2 = self.env['ojt.assignment'].create({'name': 'Tugas 2', 'batch_id': self.batch.id, 'max_score': 100.0, 'weight': 1.0})

        participant = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner.id,
            'mentor_score': 80.0,
        })
        
        self.env['ojt.assignment.submit'].create({'participant_id': participant.id, 'assignment_id': assignment1.id, 'score': 90.0, 'state': 'scored'})
        self.env['ojt.assignment.submit'].create({'participant_id': participant.id, 'assignment_id': assignment2.id, 'score': 60.0, 'state': 'scored'})
        
        # 1. Buat objek mock yang akan kita kembalikan
        mock_survey_input = self.env['survey.user_input'].new({'scoring_percentage': 75.0})
        
        # 2. Gunakan patch dengan path string yang lengkap dan benar
        #    Targetnya adalah metode 'search' di dalam model 'survey.user_input' yang diakses oleh environment Odoo
        with patch.object(type(self.env['survey.user_input']), 'search', return_value=mock_survey_input):
            
            # Di dalam blok ini, setiap kali kode Odoo memanggil self.env['survey.user_input'].search(...),
            # panggilannya akan dialihkan dan mengembalikan 'mock_survey_input' kita.
            
            participant.invalidate_recordset(['score_avg', 'score_final'])
            
            self.assertAlmostEqual(participant.score_avg, 80.0, places=2, msg="Nilai rata-rata tugas (score_avg) salah hitung.")
            self.assertAlmostEqual(participant.score_final, 72.0, places=2, msg="Nilai akhir (score_final) salah hitung.")

    def test_04_prevent_enrollment_in_ongoing_batch(self):
        """Tes: Sistem harus menolak penambahan peserta ke batch yang sudah berjalan."""
        self.batch.write({'state': 'ongoing'})

        with self.assertRaises(ValidationError, msg="Seharusnya gagal menambahkan peserta ke batch yang 'ongoing'."):
            self.env['ojt.participant'].create({
                'batch_id': self.batch.id,
                'partner_id': self.env['res.partner'].create({'name': 'Peserta Terlambat'}).id,
            })

    def test_05_email_sent_on_mentor_score(self):
        """
        Tes: Email harus terkirim saat mentor_score diisi untuk pertama kali, tapi tidak saat dikoreksi.
        """
        # --- Bagian 1: Tes pengiriman email saat nilai pertama kali diberikan ---
        participant = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner.id,
        })
        self.assertEqual(participant.mentor_score, 0.0, "Skor awal seharusnya 0.")
        initial_mail_count = self.env['mail.mail'].search_count([])

        # Aksi: Mentor memberikan nilai
        participant.write({'mentor_score': 90.0})

        # Verifikasi
        final_mail_count = self.env['mail.mail'].search_count([])
        self.assertEqual(final_mail_count, initial_mail_count + 1, "Seharusnya ada 1 email baru yang dibuat saat skor pertama kali diberikan.")

        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(new_email.email_to, self.partner.email)
        self.assertIn("Evaluasi Akhir dari Mentor", new_email.subject)
        self.assertIn("90", new_email.body_html)

        # --- Bagian 2: Tes TIDAK ada email saat nilai dikoreksi ---
        # Aksi: Mentor mengoreksi nilai dari 90 menjadi 95
        participant.write({'mentor_score': 95.0})

        # Verifikasi
        count_after_correction = self.env['mail.mail'].search_count([])
        self.assertEqual(count_after_correction, final_mail_count, "Seharusnya TIDAK ada email baru yang dibuat saat skor dikoreksi.")