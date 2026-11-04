akg_payment_receipt_report - Odoo 20
====================================
Payment Receipt / Refund Confirmation (account.payment) in the AKG look: header with logo,
teal title, info block (date, customer, amount, method, memo), table Invoice Date / Invoice Number /
Reference / Amount with "Due Amount for ..." rows, footer with QR.

Title by payment type: Payment Receipt (customer in), Refund Confirmation (customer out),
Payment Confirmation (vendor out), Refund Receipt (vendor in).
If no invoice is reconciled (e.g. POS refund) the payment itself is shown as one row.

Needs: akg_doc_reports (already installed).

Install: ./odoo-bin -c <conf> -d <db> -i akg_payment_receipt_report --stop-after-init
Update : ./odoo-bin -c <conf> -d <db> -u akg_payment_receipt_report --stop-after-init

Amount decimals: AKGP_DIGITS in models/account_payment.py (default 4, e.g. 538.3350 OMR).
Texts / labels: views/report_payment.xml.  Data: models/account_payment.py (_akgp_*).
