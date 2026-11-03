akg_proforma_report - Odoo 20
=============================
Pro-Forma Invoice PDF (sale.order) in the AKG look (same as Quotation / Order).
The module has its OWN Print-menu action "PRO-FORMA Invoice" (no group needed).

Needs: akg_report_layout + akg_doc_reports (already installed).

Update (module already installed):
  ./odoo-bin -c <conf> -d <db> -u akg_proforma_report --stop-after-init
Install:
  ./odoo-bin -c <conf> -d <db> -i akg_proforma_report --stop-after-init
Then hard-refresh the browser (Ctrl+F5): the Print menu is cached by the web client.

Info row / lines / totals / notes come from akg_doc_reports (models/sale_order.py);
only the title "Pro-Forma Invoice #" is specific to this module.
