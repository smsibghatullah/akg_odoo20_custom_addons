odoo.define('pos_credit_limit.pos_credit_limit_check', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');

    const PosCreditLimitCheck = (PaymentScreen) =>
        class extends PaymentScreen {
            async validateOrder(isForceValidate) {
                const order = this.env.pos.get_order();
                const partner = order.get_partner();
                const paymentlines = order.get_paymentlines();

                // 🐞 Debug logs
                console.log("🔍 All Payment Lines:");
                paymentlines.forEach((p) => {
                    console.log("Payment Line:", p);
                    console.log("Payment Method:", p.payment_method);
                    console.log("Is Cash Journal?", p.payment_method.use_cash_journal);
                });
                
               
                const isAnyNonCash = order.get_paymentlines().some(
                    (p) => p.payment_method.type === 'pay_later'
                );

                if (partner && isAnyNonCash) {
                    

                    try {
                        const result = await rpc.query({
                            model: 'res.partner',
                            method: 'check_partner_credit_limit',
                            args: [partner.id, order.get_total_with_tax(), isAnyNonCash],
                        });

                        if (!result.allowed) {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Credit Limit Exceeded'),
                                body: this.env._t(
                                    "Customer's credit limit has been exceeded. Non-cash payment not allowed."
                                ),
                            });
                            return;
                        }
                    } catch (error) {
                        console.error('Credit limit check error:', error);
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: this.env._t('Could not check credit limit.'),
                        });
                        return;
                    }
                }

                await super.validateOrder(isForceValidate);
            }
        };

    Registries.Component.extend(PaymentScreen, PosCreditLimitCheck);

    return PaymentScreen;
});
