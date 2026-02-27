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

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * Overrides printReceipt to load invoice data if not available
     * This works for both ReceiptScreen and TicketScreen printing
     * Uses loading flags to prevent duplicate server calls
     */
    async printReceipt({ order = this.getOrder(), basic = false, printBillActionTriggered = false } = {}) {
        // If the order has an invoice (account_move) but we don't have the data loaded, load it
        const hasInvoice = order.raw && order.raw.account_move;
        const hasInvoiceData = order.getInvoice();
        const isLoading = order.is_invoice_loading();

        if (hasInvoice && !hasInvoiceData && !isLoading) {
            order.set_invoice_loading(true);
            try {
                // Ensure order.id is a valid number
                const orderId = typeof order.id === 'number' ? order.id : order.backendId;
                if (orderId) {
                    const invoiceData = await this.data.orm.call(
                        "pos.order",
                        "get_invoice",
                        [[orderId]]
                    );
                    order.set_invoice(invoiceData || null);
                }
            } catch (error) {
                console.error("[l10n_co_edi_jorels_pos] Error loading invoice data:", error);
                order.set_invoice_loading(false);
            }
        }

        // Call original method
        return super.printReceipt({ order, basic, printBillActionTriggered });
    },

    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.partner = order.getPartner();
        result.invoice = order.getInvoice();
        // Ensure country is available in the correct format (using country as in Odoo 17)
        if (this.company.country_id) {
            result.company.country = {
                code: this.company.country_id.code
            };
        }
        return result;
    },
});
