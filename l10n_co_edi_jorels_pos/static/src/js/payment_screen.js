/** @odoo-module */

// Jorels S.A.S. - Copyright (2019-2024)
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
    toggleIsToElectronicInvoice() {
        this.currentOrder.set_to_electronic_invoice(!this.currentOrder.is_to_electronic_invoice());
    },
    async _postPushOrderResolve(order, order_server_ids) {
        if (order.is_to_invoice()) {
            const result = await this.orm.call(
                "pos.order",
                "get_invoice",
                [order_server_ids]
            );
            order.set_invoice(result || null);
        }
        return super._postPushOrderResolve(...arguments);
    },
});
