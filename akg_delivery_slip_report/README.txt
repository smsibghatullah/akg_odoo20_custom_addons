akg_delivery_slip_report - Odoo 20
==================================
Delivery Slip (stock.picking) in the AKG look: header with logo, Customer Address /
Warehouse Address (address of the picking's warehouse, NOT the customer delivery address), picking reference as teal title, Order + Shipping Date, table
Product / Ordered / Delivered (Lot/Serial column only when lots are used), footer with QR.

Needs: akg_report_layout + akg_doc_reports (already installed).

Install: ./odoo-bin -c <conf> -d <db> -i akg_delivery_slip_report --stop-after-init
Update : ./odoo-bin -c <conf> -d <db> -u akg_delivery_slip_report --stop-after-init

Texts / labels: views/report_delivery.xml.  Data: models/stock_picking.py (_akgd_*).
