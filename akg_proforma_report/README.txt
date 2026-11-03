akg_proforma_report - Odoo 20
=============================
Pro-Forma Invoice PDF (sale.order) in the AKG look (same as Quotation / Order).

Needs: akg_report_layout and akg_doc_reports (already in your reports.zip)
       + the Pro-Forma action enabled: Settings > Sales > "Pro-Forma Invoice".

Install: copy folder to the addons path, then
  ./odoo-bin -c <conf> -d <db> -i akg_proforma_report --stop-after-init
Update:
  ./odoo-bin -c <conf> -d <db> -u akg_proforma_report --stop-after-init

Info row / lines / totals / notes come from akg_doc_reports (models/sale_order.py);
only the title "Pro-Forma Invoice #" is specific to this module.
