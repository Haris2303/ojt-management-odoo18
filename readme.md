# OJT Management Module for Odoo 18

Aplikasi **OJT (On-the-Job Training) Management** ini dibuat menggunakan **Odoo 18** untuk mempermudah pengelolaan peserta OJT, batch, assignment, event, attendance, dan laporan terkait.

---

## Fitur Utama

- Manajemen peserta OJT
- Manajemen batch OJT
- Manajemn Event (Agenda)
- Attendance Peserta
- Assignment Peserta
- Assignment Submit peserta
- Certificate OJT
- Portal untuk peserta memantau progress
- Laporan Dashboard

---

## Persyaratan

- Odoo 18
- Python 3.12+ (sesuai environment Odoo)
- PostgreSQL 15+
- Modul tambahan Odoo (jika ada dependencies, tuliskan di sini)

---

## Instalasi Modul

1. Clone atau download modul ini ke folder `addons` Odoo:

```bash
cd /path/to/your/odoo/addons
git clone <repo-url> ojt_management
```

2. Restart Odoo Server

```bash
# Linux example
./odoo-bin -c /etc/odoo/odoo.conf
```

3. Masuk ke Odoo -> Apps -> Update Apps List -> Cari OJT Management -> Install

## Konfigurasi Email (Opsional)

Jika ingin fitur email otomatis (misal untuk notifikasi assignment):

1. Konfigurasikan Mail Server di Odoo:

   Settings → Technical → Email → Outgoing Mail Servers

2. Tes email menggunakan Mail Test untuk memastikan terkirim.

## Run Test In Powershell

Semua unit test

```bash
docker exec -it odoo18-odoo-1 /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo18 --test-enable --workers=0 --http-port=0 --stop-after-init -i solvera_ojt_core
```

Method tertentu

```bash
docker exec -it odoo18-odoo-1 /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo18 --test-enable --workers=0 --http-port=0 --stop-after-init --test-tags solvera_ojt_core.tests.test_ojt_assignment.TestOjtAssignment:test_email_sent_on_new_assignment
```

## License

_Tulis license modul kamu di sini (misal MIT, LGPL, atau proprietary)._
