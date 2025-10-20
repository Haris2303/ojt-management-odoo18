# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.fields import Date
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo import fields

class TestOjtBatch(TransactionCase):
    """
    Kelompok tes untuk memvalidasi logika bisnis dari model ojt.batch.
    """

    def setUp(self, *args, **kwargs):
        """Siapkan data awal yang dibutuhkan untuk semua tes."""
        super(TestOjtBatch, self).setUp(*args, **kwargs)

        self.batch = self.env['ojt.batch'].create({
            'name': 'Test Batch for Email',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'state': 'recruit', # Mulai dari state 'recruit'
        })
        
        # Buat sequence untuk kode batch agar tes tidak bergantung pada data yang ada
        self.env['ir.sequence'].create({
            'name': 'OJT Batch Test Sequence',
            'code': 'ojt.batch',
            'padding': 4,
            'prefix': 'TEST/%(year)s/',
        })

        # Buat data partner dan participant untuk digunakan di berbagai tes
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Participant Partner',
            'email': 'ahostweb13@gmail.com'
        })

        self.participant = self.env['ojt.participant'].create({
            'partner_id': self.test_partner.id,
            'batch_id': self.batch.id
        })

    def test_01_batch_creation_with_sequence(self):
        """Tes: Batch baru harus mendapatkan kode dari sequence."""
        batch = self.env['ojt.batch'].create({
            'name': 'Batch Test Sequence',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })
        
        # Verifikasi bahwa kode tidak lagi default '/' dan mengikuti format sequence
        self.assertNotEqual(batch.code, '/', "Kode batch seharusnya sudah digenerate oleh sequence.")
        self.assertIn('TEST/2025/', batch.code, "Format kode batch tidak sesuai dengan sequence.")

    def test_02_date_constraint_validation(self):
        """Tes: Sistem harus menolak jika start_date > end_date."""
        
        # Gunakan assertRaises untuk menangkap ValidationError yang diharapkan
        with self.assertRaises(ValidationError, msg="Seharusnya muncul ValidationError jika tanggal tidak valid."):
            self.env['ojt.batch'].create({
                'name': 'Batch Tanggal Salah',
                'start_date': '2025-12-10',
                'end_date': '2025-12-01', # Tanggal akhir sebelum tanggal mulai
            })

    def test_03_state_transitions_and_participant_update(self):
        """Tes: Transisi state dan dampaknya pada state peserta."""
        batch = self.env['ojt.batch'].create({
            'name': 'Batch Test Transisi',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })
        
        participant = self.env['ojt.participant'].create({
            'batch_id': batch.id,
            'partner_id': self.test_partner.id,
            # State default participant adalah 'active'
        })

        # Verifikasi state awal
        self.assertEqual(batch.state, 'draft', "State awal batch seharusnya 'draft'.")
        self.assertEqual(participant.state, 'active', "State awal peserta seharusnya 'active'.")

        # Transisi ke Recruitment
        batch.action_recruit()
        self.assertEqual(batch.state, 'recruit', "State seharusnya berubah menjadi 'recruit'.")
        
        # Transisi ke Ongoing
        batch.action_ongoing()
        self.assertEqual(batch.state, 'ongoing', "State seharusnya berubah menjadi 'ongoing'.")

        # Transisi ke Done dan verifikasi state participant
        batch.action_done()
        self.assertEqual(batch.state, 'done', "State batch seharusnya berubah menjadi 'done'.")
        # Periksa ulang state participant setelah di-refresh dari database
        participant.invalidate_recordset()
        self.assertEqual(participant.state, 'completed', "State peserta seharusnya berubah menjadi 'completed' saat batch selesai.")

    def test_04_participant_count_computation(self):
        """Tes: Compute field 'participant_count' harus menghitung dengan benar."""
        batch = self.env['ojt.batch'].create({
            'name': 'Batch Test Hitung Peserta',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })
        
        # Verifikasi jumlah awal
        self.assertEqual(batch.participant_count, 0, "Awalnya, jumlah peserta harus 0.")

        # Tambah satu peserta
        self.env['ojt.participant'].create({
            'batch_id': batch.id,
            'partner_id': self.test_partner.id,
        })
        
        # Refresh batch untuk memicu ulang compute method
        batch.invalidate_recordset()
        self.assertEqual(batch.participant_count, 1, "Setelah menambah satu peserta, jumlahnya harus 1.")

    def test_05_progress_ratio_computation(self):
        """Tes: Compute field 'progress_ratio' harus menghitung rata-rata skor dengan benar."""
        # ... (kode pembuatan batch dan assignment tidak berubah)
        # 1. Buat Batch dengan semua field yang dibutuhkan
        batch = self.env['ojt.batch'].create({
            'name': 'Batch Test Progress Ratio',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })

        # 2. Buat satu master tugas untuk batch ini
        assignment = self.env['ojt.assignment'].create({
            'name': 'Tugas Wajib',
            'batch_id': batch.id,
            'max_score': 100.0,
        })

        # Buat peserta dengan menyertakan mentor_score
        participant_a = self.env['ojt.participant'].create({
            'batch_id': batch.id,
            'partner_id': self.env['res.partner'].create({'name': 'Peserta A'}).id,
            'mentor_score': 80.0, # <-- Tambahkan nilai mentor
        })
        participant_b = self.env['ojt.participant'].create({
            'batch_id': batch.id,
            'partner_id': self.env['res.partner'].create({'name': 'Peserta B'}).id,
            'mentor_score': 60.0, # <-- Tambahkan nilai mentor
        })

        # Buat data pengumpulan tugas (tidak berubah)
        self.env['ojt.assignment.submit'].create({
            'assignment_id': assignment.id,
            'participant_id': participant_a.id,
            'score': 100.0,
            'state': 'scored',
        })
        self.env['ojt.assignment.submit'].create({
            'assignment_id': assignment.id,
            'participant_id': participant_b.id,
            'score': 50.0,
            'state': 'scored',
        })

        batch.invalidate_recordset(['progress_ratio'])

        # Hitung ulang nilai yang diharapkan:
        # Skor A = (100 * 0.7) + (80 * 0.2) + (0 * 0.1) = 70 + 16 = 86.0
        # Skor B = (50 * 0.7) + (60 * 0.2) + (0 * 0.1) = 35 + 12 = 47.0
        # Rata-rata = (86.0 + 47.0) / 2 = 133.0 / 2 = 66.5
        expected_ratio = 66.5

        self.assertEqual(batch.progress_ratio, expected_ratio, "Progress ratio seharusnya adalah rata-rata dari skor akhir semua peserta.")

    def test_06_cron_job_state_updates(self):
        """Tes: Cron job harus mengubah status batch secara otomatis berdasarkan tanggal."""
        
        # Buat batch yang seharusnya dimulai besok dan berakhir lusa
        batch_to_start = self.env['ojt.batch'].create({
            'name': 'Batch Test Cron Start',
            'start_date': Date.to_string(Date.today()), # Mulai hari ini
            'end_date': '2025-12-31',
            'state': 'recruit', # Status awal untuk dites
        })

        # Panggil cron job
        self.env['ojt.batch']._cron_update_batch_states()
        
        # Verifikasi bahwa statusnya berubah menjadi 'ongoing'
        self.assertEqual(batch_to_start.state, 'ongoing', "Cron job seharusnya mengubah state menjadi 'ongoing' jika start_date sudah tercapai.")

        # Sekarang, kita 'pura-pura' berada di masa depan setelah batch selesai
        future_date = Date.from_string('2026-01-15')
        with patch('odoo.fields.Date.today', return_value=future_date):
            # Panggil lagi cron job di "masa depan"
            self.env['ojt.batch']._cron_update_batch_states()
        
        # Verifikasi bahwa statusnya sekarang 'done'
        self.assertEqual(batch_to_start.state, 'done', "Cron job seharusnya mengubah state menjadi 'done' jika end_date telah berlalu.")

    def test_07_reverting_done_state(self):
        """Tes: Mengubah state dari 'done' harus mengembalikan state peserta."""
        batch = self.env['ojt.batch'].create({
            'name': 'Batch Test Revert State',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
        })
        participant = self.env['ojt.participant'].create({
            'batch_id': batch.id,
            'partner_id': self.test_partner.id,
        })

        # Selesaikan batch, state peserta seharusnya menjadi 'completed'
        batch.action_done()
        self.assertEqual(participant.state, 'completed', "State peserta seharusnya 'completed' saat batch selesai.")

        # Kembalikan batch ke draft
        batch.write({'state': 'draft'})

        # Periksa kembali state peserta
        self.assertEqual(participant.state, 'active', "State peserta seharusnya kembali ke 'active' saat batch di-revert.")

    def test_08_prevent_enrollment_in_ongoing_batch(self):
        """Tes: Sistem harus menolak penambahan peserta baru ke batch yang sudah berjalan."""
        
        # 1. Buat batch dan set statusnya ke 'ongoing'
        ongoing_batch = self.env['ojt.batch'].create({
            'name': 'Batch Ongoing Test',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
            'state': 'ongoing', # Langsung set ke ongoing untuk tes
        })

        # 2. Verifikasi bahwa penambahan peserta GAGAL
        with self.assertRaises(ValidationError, msg="Seharusnya gagal menambahkan peserta ke batch yang 'ongoing'."):
            self.env['ojt.participant'].create({
                'batch_id': ongoing_batch.id,
                'partner_id': self.test_partner.id,
            })
            
        # 3. (Opsional) Verifikasi bahwa penambahan ke batch 'draft' masih BISA
        draft_batch = self.env['ojt.batch'].create({
            'name': 'Batch Draft Test',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
            'state': 'draft',
        })

        # Blok ini seharusnya tidak menghasilkan error
        try:
            self.env['ojt.participant'].create({
                'batch_id': draft_batch.id,
                'partner_id': self.test_partner.id,
            })
        except ValidationError:
            self.fail("Seharusnya BISA menambahkan peserta ke batch yang masih 'draft'.")

    def test_09_email_sent_on_batch_ongoing(self):
        """
        Tes Skenario: Email harus terkirim saat status batch diubah menjadi 'ongoing'.
        """
        # Hitung jumlah email yang ada di antrian sebelum aksi
        initial_mail_count = self.env['mail.mail'].search_count([])

        # Lakukan aksi: ubah status batch menjadi 'ongoing'
        self.batch.action_ongoing()

        # Hitung kembali jumlah email setelah aksi
        final_mail_count = self.env['mail.mail'].search_count([])

        # Verifikasi: Pastikan ada 1 email baru yang dibuat
        self.assertEqual(final_mail_count, initial_mail_count + 1, 
                            "Seharusnya ada satu email baru yang dibuat saat batch menjadi 'ongoing'.")

        # Verifikasi Lanjutan: Periksa detail email yang terkirim
        # Cari email terakhir yang dibuat
        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)
        
        self.assertEqual(new_email.email_to, self.test_partner.email,
                            "Penerima email tidak sesuai.")
        
        self.assertIn(self.batch.name, new_email.subject,
                        "Subjek email seharusnya mengandung nama batch.")
    
    def test_10_email_sent_on_batch_done(self):
        """
        Tes Skenario: Email harus terkirim ke setiap peserta saat status batch diubah menjadi 'done'.
        """
        # --- Arrange (Persiapan) ---
        # Menghitung jumlah email yang ada di antrean sebelum aksi
        initial_mail_count = self.env['mail.mail'].search_count([])

        # --- Act (Aksi) ---
        # Lakukan aksi: ubah status batch menjadi 'done'
        self.batch.action_done()

        # --- Assert (Verifikasi) ---
        # Hitung kembali jumlah email setelah aksi
        final_mail_count = self.env['mail.mail'].search_count([])

        # 1. Verifikasi: Pastikan ada 1 email baru yang dibuat
        self.assertEqual(final_mail_count, initial_mail_count + 1, 
                            "Seharusnya ada satu email baru yang dibuat saat batch selesai (done).")

        # 2. Verifikasi Lanjutan: Periksa detail email yang terkirim
        # Cari email terakhir yang dibuat untuk memastikan kita memeriksa email yang benar
        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)
        
        # Periksa penerima
        self.assertEqual(new_email.email_to, self.test_partner.email,
                            "Penerima email tidak sesuai dengan email peserta.")
        
        # Periksa subjek email
        self.assertIn("Selamat! Anda Telah Menyelesaikan Program OJT", new_email.subject,
                        "Subjek email tidak sesuai dengan template untuk batch selesai.")
        self.assertIn(self.batch.name, new_email.subject,
                        "Subjek email seharusnya mengandung nama batch.")
        
        # Periksa body email, pastikan URL portal ada di dalamnya
        self.assertIn('/my/dashboard?participant_id=', new_email.body_html,
                        "Body email seharusnya mengandung link ke dashboard portal peserta.")
        
    def test_email_sent_on_survey_added(self):
        """
        Tes Skenario: Email harus terkirim saat survei ditambahkan ke batch untuk pertama kalinya.
        """
        # --- Arrange ---
        # Buat data yang diperlukan
        survey = self.env['survey.survey'].create({'title': 'Survei Kepuasan OJT'})
        partner = self.env['res.partner'].create({'name': 'Peserta Survei', 'email': 'survey.participant@example.com'})
        participant = self.env['ojt.participant'].create({'partner_id': partner.id, 'batch_id': self.batch.id})

        self.assertFalse(self.batch.survey_id, "Batch seharusnya belum memiliki survei di awal.")
        initial_mail_count = self.env['mail.mail'].search_count([])

        # --- Act ---
        # Mentor menambahkan survei ke batch
        self.batch.write({'survey_id': survey.id})

        # --- Assert ---
        final_mail_count = self.env['mail.mail'].search_count([])
        self.assertEqual(final_mail_count, initial_mail_count + 1, "Seharusnya ada 1 email baru yang dibuat.")

        new_email = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(new_email.email_to, partner.email)
        self.assertIn("Undangan Mengisi Survei", new_email.subject)
        self.assertIn('/survey/start/', new_email.body_html)