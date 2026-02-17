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

import {ReceiptScreen} from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {useTrackedAsync} from "@point_of_sale/app/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        // Call original setup first
        super.setup();

        // Store reference to orm
        this.orm = useService("orm");

        // Override doFullPrint to load invoice data before printing
        this.doFullPrint = useTrackedAsync(async () => {
            await this._loadInvoiceDataIfNeeded();
            return this.pos.printReceipt();
        });

        // Override doBasicPrint to load invoice data before printing
        this.doBasicPrint = useTrackedAsync(async () => {
            await this._loadInvoiceDataIfNeeded();
            return this.pos.printReceipt({ basic: true });
        });
    },

    /**
     * Loads invoice data if the order has an invoice but the data is not loaded
     */
    async _loadInvoiceDataIfNeeded() {
        const order = this.currentOrder;

        // If the order has an invoice (account_move) but we don't have the data loaded, load it
        const hasInvoice = order.raw && order.raw.account_move;
        const hasInvoiceData = order.get_invoice();

        if (hasInvoice && !hasInvoiceData) {
            try {
                // Ensure order.id is a valid number
                const orderId = typeof order.id === 'number' ? order.id : order.backendId;
                if (!orderId) {
                    return;
                }

                const invoiceData = await this.orm.call(
                    "pos.order",
                    "get_invoice",
                    [[orderId]]
                );
                order.set_invoice(invoiceData || null);
            } catch (error) {
                console.error("[l10n_co_edi_jorels_pos] Error loading invoice data:", error);
            }
        }
    },
});
