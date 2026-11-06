/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";

patch(ProductCard.prototype, {
    get tilePrice() {
        try {
            const product = this.props.product;
            if (!product) {
                return "";
            }
            let amount = Number(product.list_price || 0);
            let isFrom = false;
            // Variant products: show the lowest price (base + smallest extra)
            const lines = product.attribute_line_ids || [];
            if (lines.length) {
                const extras = [];
                for (const line of lines) {
                    for (const val of line.product_template_value_ids || []) {
                        extras.push(Number(val.price_extra || 0));
                    }
                }
                if (extras.length) {
                    const min = Math.min(...extras);
                    const max = Math.max(...extras);
                    amount += min;
                    isFrom = max !== min;
                }
            }
            const fmt = this.env?.utils?.formatCurrency;
            const text = fmt ? fmt(amount) : amount.toFixed(3);
            return isFrom ? `from ${text}` : text;
        } catch (e) {
            return "";
        }
    },
});
