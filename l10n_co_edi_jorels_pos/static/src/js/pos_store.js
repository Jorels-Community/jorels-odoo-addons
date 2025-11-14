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

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.is_colombian_country()) {
            this.type_regimes = loadedData['l10n_co_edi_jorels.type_regimes'];
            this.type_liabilities = loadedData['l10n_co_edi_jorels.type_liabilities'];
            this.municipalities = loadedData['l10n_co_edi_jorels.municipalities'];
            this.l10n_latam_identification_types = loadedData['l10n_latam.identification.type'];
        }
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (order && this.company?.country?.code === "CO") {
            result.partner = order.get_partner();
            result.invoice = order.invoice;
        }
        return result;
    },
});
