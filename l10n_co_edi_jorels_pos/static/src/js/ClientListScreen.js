odoo.define('l10n_co_edi_jorels_pos.ClientListScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientListScreen = require('point_of_sale.ClientListScreen');

    const JClientListScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
                this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner,
                    this._getDefaultPartner()
                );
            }

            _getDefaultPartner() {
                if (this.env.pos.company.ei_enable && this.env.pos.company.ei_set_default_partner_data) {
                    return {
                        name: 'Consumidor Final',
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                        vat: '222222222222',
                        company_type: 'person',
                        city: this.env.pos.company.city,
                        l10n_latam_identification_type_id: [this.env.pos.l10n_latam_identification_types.find(o => o.l10n_co_document_code=='national_citizen_id')['id']],
                        type_regime_id: [2],
                        type_liability_id: [29],
                        municipality_id: this.env.pos.company.municipality_id
                    };
                }
                
                return {};
            }

            deactivateEditMode() {
                super.deactivateEditMode();
                this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner, this._getDefaultPartner());
                this.render();
            }
        };

    Registries.Component.extend(ClientListScreen, JClientListScreen);

    return ClientListScreen;
});