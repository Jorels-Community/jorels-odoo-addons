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

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.to_electronic_invoice = false;
    },
    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.to_electronic_invoice = false;
        if (this.account_move){
            this.invoice = this.get_invoice();
            this.invoice.then(invoice => this.invoice = invoice);
        }
    },
    export_as_JSON() {
        var json = super.export_as_JSON(...arguments);
        json.to_electronic_invoice = this.to_electronic_invoice ? this.to_electronic_invoice : false;
        return json;
    },
    export_for_printing() {
        var receipt = super.export_for_printing(...arguments);
        if (this.invoice){
            receipt.invoice = this.invoice;
        }
        return receipt;
    },
    set_invoice(invoice){
        this.invoice = invoice;
    },
    get_invoice(){
        self = this;
        const result = this.env.services.orm.call(
            "pos.order",
            "get_invoice",
            [self.backendId]
        );
        return result;
    },
    set_to_electronic_invoice(to_electronic_invoice) {
        this.assert_editable();
        this.to_electronic_invoice = to_electronic_invoice;
    },
    is_to_electronic_invoice(){
        return this.to_electronic_invoice;
    },
});
