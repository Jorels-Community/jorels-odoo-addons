odoo.define('l10n_co_edi_jorels_pos.ClientDetailsEdit', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');

    const JClientDetailsEdit = (ClientDetailsEdit) =>
        class extends ClientDetailsEdit {
            constructor() {
                super(...arguments);
                this.intFields.push(
                    'l10n_latam_identification_type_id',
                    'type_regime_id',
                    'type_liability_id',
                    'municipality_id'
                );
                const partner = this.props.partner;
                this.changes = Object.assign({}, this.changes,
                    {
                        vat: partner.vat,
                        company_type: partner.company_type,
                        city: partner.city,
                        l10n_latam_identification_type_id: partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0],
                        type_regime_id: partner.type_regime_id && partner.type_regime_id[0],
                        type_liability_id: partner.type_liability_id && partner.type_liability_id[0],
                        municipality_id: partner.municipality_id && partner.municipality_id[0]
                    }
                );
            }
        };

    Registries.Component.extend(ClientDetailsEdit, JClientDetailsEdit);

    return ClientDetailsEdit;
});