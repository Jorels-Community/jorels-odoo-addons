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

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        // Add partner (already available synchronously in the model)
        result.partner = this.getPartner();
        // Use locally stored invoice data (previously loaded asynchronously)
        result.invoice = this.getInvoice();
        // Ensure headerData also has the fields for ReceiptHeader
        if (result.headerData) {
            result.headerData.partner = result.partner;
            result.headerData.invoice = result.invoice;
        }
        return result;
    },
    /**
     * Stores the invoice data in the order.
     * Called from payment_screen.js when invoicing the order.
     */
    set_invoice(invoice){
        this.invoice = invoice;
        this._invoice_loading = false;  // Reset loading flag when data is stored
    },
    /**
     * Returns the locally stored invoice data.
     * Returns null if there is no invoice or if the data has not been loaded yet.
     */
    getInvoice(){
        // Return locally stored data (synchronous)
        // Data is loaded in payment_screen.js at the time of invoicing
        return this.invoice || null;
    },
    /**
     * Checks if invoice data is currently being loaded.
     * Prevents multiple simultaneous server calls.
     */
    is_invoice_loading(){
        return this._invoice_loading || false;
    },
    /**
     * Sets the loading flag to prevent duplicate server calls.
     */
    set_invoice_loading(loading){
        this._invoice_loading = loading;
    },
});
