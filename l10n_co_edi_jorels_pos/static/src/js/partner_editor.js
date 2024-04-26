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

import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerDetailsEdit.prototype, {
    setup(){
        super.setup(...arguments);
        if (this.pos.is_colombian_country()) {
            this.intFields.push(
                'l10n_latam_identification_type_id',
                'type_regime_id',
                'type_liability_id',
                'municipality_id'
            );
            const partner = this.props.partner;
            this.changes.company_type = partner.company_type
            this.changes.l10n_latam_identification_type_id = partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0]
            this.changes.type_regime_id = partner.type_regime_id && partner.type_regime_id[0]
            this.changes.type_liability_id = partner.type_liability_id && partner.type_liability_id[0]
            this.changes.municipality_id = partner.municipality_id && partner.municipality_id[0]
            this.changes.email_edi = partner.email_edi || ""
        }
    },
});
