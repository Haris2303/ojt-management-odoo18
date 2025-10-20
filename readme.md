## Run Test In Powershell

Semua unit test

```bash
docker exec -it odoo18-odoo-1 /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo18 --test-enable --workers=0 --http-port=0 --stop-after-init -i solvera_ojt_core
```

Method tertentu

```bash
docker exec -it odoo18-odoo-1 /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo18 --test-enable --workers=0 --http-port=0 --stop-after-init --test-tags solvera_ojt_core.tests.test_ojt_assignment.TestOjtAssignment:test_email_sent_on_new_assignment
```
