akg_doc_reports - Odoo 20
=========================
Quotation / Sales Order, Purchase Order / RFQ and Picking Operations reports
in the Odoo 16 AKG look (header with logo, footer with QR, Oswald-like font).

Install:  copy folder to the addons path, then
          ./odoo-bin -c <conf> -d <db> -i akg_doc_reports
Update:   ./odoo-bin -c <conf> -d <db> -u akg_doc_reports
          (also run it again after upgrading sale / purchase / stock)

Editable values: models/res_company.py -> _akgr_footer_vals()
                 (Tax card no., CR no., Arabic company name, "Thank you" text)
Font:     put Oswald-Regular.ttf / Oswald-Bold.ttf in static/src/fonts/ (see README there).
