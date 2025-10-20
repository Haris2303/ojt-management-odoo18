# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import date

class TestCertificateFlow(TransactionCase):
    """
    Menguji alur kerja end-to-end dari kelayakan peserta hingga penerbitan sertifikat.
    Tes ini meniru alur kerja yang realistis.
    """

    def setUp(self, *args, **kwargs):
        """Siapkan data master yang komprehensif untuk alur kerja."""
        super(TestCertificateFlow, self).setUp(*args, **kwargs)

        # 1. Buat Batch dengan kriteria kelulusan
        self.batch = self.env['ojt.batch'].create({
            'name': 'OJT Full Flow Test Batch',
            'start_date': '2025-11-01',
            'end_date': '2025-11-30',
            'certificate_rule_attendance': 80.0,
            'certificate_rule_score': 70.0,
        })

        # 2. Buat Sesi Wajib untuk absensi
        event = self.env['event.event'].create({'name': 'Sesi Wajib Full Flow'})
        self.event_link = self.env['ojt.event.link'].create({
            'batch_id': self.batch.id,
            'event_id': event.id,
            'is_mandatory': True,
        })

        # 3. Buat Tugas untuk penilaian
        self.assignment = self.env['ojt.assignment'].create({
            'name': 'Tugas Final Full Flow',
            'batch_id': self.batch.id,
            'max_score': 100.0,
            'weight': 1.0, # Bobot sederhana untuk tes ini
        })
        
        # 4. Buat Peserta yang akan LULUS
        self.partner_lulus = self.env['res.partner'].create({'name': 'Peserta Lulus Flow'})
        self.participant_lulus = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner_lulus.id,
            'mentor_score': 85.0, # Nilai mentor tinggi
        })
        
        # Buat absensi LULUS (1 dari 1 sesi wajib = 100%)
        self.env['ojt.attendance'].create({
            'participant_id': self.participant_lulus.id,
            'event_link_id': self.event_link.id,
            'presence': 'present',
        })
        
        # Buat submit tugas LULUS
        self.env['ojt.assignment.submit'].create({
            'participant_id': self.participant_lulus.id,
            'assignment_id': self.assignment.id,
            'score': 90.0, # Nilai tugas tinggi
            'state': 'scored',
        })
        
        # Set status peserta menjadi completed
        self.participant_lulus.write({'state': 'completed'})

        # 5. Buat Peserta yang akan GAGAL (karena absensi kurang)
        self.partner_gagal = self.env['res.partner'].create({'name': 'Peserta Gagal Flow'})
        self.participant_gagal = self.env['ojt.participant'].create({
            'batch_id': self.batch.id,
            'partner_id': self.partner_gagal.id,
            'mentor_score': 85.0,
        })
        # TIDAK ADA absensi untuk peserta ini, jadi attendance_rate = 0%
        self.participant_gagal.write({'state': 'completed'})

        # Flush semua data untuk memastikan compute fields terhitung
        self.env.flush_all()

    def test_01_wizard_eligibility_check_is_correct(self):
        """Tes: Wizard harus bisa mengidentifikasi peserta yang layak dengan benar."""

        wizard = self.env['ojt.generate.certificates.wizard'].create({
            'batch_id': self.batch.id
        })
        
        # Verifikasi bahwa hanya satu peserta yang ditemukan
        self.assertEqual(wizard.participant_count, 1, "Wizard seharusnya hanya menemukan 1 peserta yang layak.")
        self.assertIn(self.participant_lulus, wizard.eligible_participant_ids, "Peserta yang lulus harus ada di daftar.")
        self.assertNotIn(self.participant_gagal, wizard.eligible_participant_ids, "Peserta yang gagal tidak boleh ada di daftar.")

    def test_02_wizard_action_generates_certificate(self):
        """Tes: Aksi wizard berhasil membuat sertifikat untuk peserta yang layak."""

        # Pastikan belum ada sertifikat
        self.assertEqual(len(self.participant_lulus.certificate_ids), 0)

        # Jalankan wizard
        wizard = self.env['ojt.generate.certificates.wizard'].create({
            'batch_id': self.batch.id
        })
        wizard.action_generate_certificates()

        # Verifikasi bahwa sertifikat telah dibuat
        self.assertEqual(len(self.participant_lulus.certificate_ids), 1, "Seharusnya ada 1 sertifikat setelah wizard dijalankan.")
        
        cert = self.participant_lulus.certificate_ids[0]
        self.assertEqual(cert.state, 'issued', "Sertifikat yang di-generate harus langsung berstatus 'issued'.")


    def test_03_wizard_action_generates_certificate(self):
        """Tes: Aksi wizard berhasil membuat sertifikat untuk peserta yang layak."""
        
        # Cek bahwa belum ada sertifikat untuk peserta ini
        existing_certs_before = self.env['ojt.certificate'].search([('participant_id', '=', self.participant_lulus.id)])
        self.assertEqual(len(existing_certs_before), 0, "Seharusnya belum ada sertifikat sebelum wizard dijalankan.")

        # Buat dan jalankan wizard
        wizard = self.env['ojt.generate.certificates.wizard'].create({
            'batch_id': self.batch.id
        })

        wizard.action_generate_certificates()

        # Cek bahwa sertifikat telah dibuat
        existing_certs_after = self.env['ojt.certificate'].search([('participant_id', '=', self.participant_lulus.id)])
        self.assertEqual(len(existing_certs_after), 1, "Seharusnya ada 1 sertifikat setelah wizard dijalankan.")
        
        cert = existing_certs_after[0]
        self.assertEqual(cert.state, 'issued', "Sertifikat yang di-generate harus langsung berstatus 'issued'.")