/** @odoo-module */

// Jorels S.A.S. - Copyright (2026)
//
// This file is part of l10n_co_edi_jorels_pos.
//
// l10n_co_edi_jorels_pos is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// l10n_co_edi_jorels_pos is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with l10n_co_edi_jorels_pos.  If not, see <https://www.gnu.org/licenses/>.
//
// email: info@jorels.com
//

import {InvoiceButton} from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import {patch} from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async _invoiceOrder() {
        // Call original method first
        await super._invoiceOrder(...arguments);

        // After invoicing, load the invoice data
        const order = this.props.order;
        if (order && order.raw?.account_move && !order.is_invoice_loading() && !order.getInvoice()) {
            order.set_invoice_loading(true);
            try {
                const invoiceData = await this.pos.data.orm.call(
                    "pos.order",
                    "get_invoice",
                    [order.id]
                );
                // Store data using the proper method
                order.set_invoice(invoiceData || null);
            } catch (error) {
                console.warn("[l10n_co_edi_jorels_pos] Could not load invoice data:", error);
                order.set_invoice(null);
            }
        }
    },
});
