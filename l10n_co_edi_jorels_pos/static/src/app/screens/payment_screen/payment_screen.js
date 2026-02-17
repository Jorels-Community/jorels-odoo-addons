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

import {patch} from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (order.is_to_invoice() && order_server_ids && order_server_ids.length > 0 && !order.is_invoice_loading()) {
            // Get the first ID from the array (corresponds to the current order)
            const orderId = order_server_ids[0];
            order.set_invoice_loading(true);

            try {
                const result = await this.orm.call(
                    "pos.order",
                    "get_invoice",
                    [[orderId]]
                );
                // Store data locally for synchronous use when printing
                order.set_invoice(result || null);
            } catch (error) {
                console.error("[l10n_co_edi_jorels_pos] Error loading invoice data:", error);
                order.set_invoice(null);
            }
        }
        // Call parent method to maintain compatibility with other modules
        return super._postPushOrderResolve(...arguments);
    },
});
