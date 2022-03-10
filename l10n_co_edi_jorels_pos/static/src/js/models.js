// Jorels S.A.S. - Copyright (2019-2022)
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

odoo.define('l10n_co_edi_jorels_pos.models', function(require) {
    "use strict";

    const { Context } = owl;
    var PosDB = require('point_of_sale.DB');
    var core = require('web.core');
    var exports = require('point_of_sale.models');
    var OrderSuper = exports.Order;
    var _t = core._t;
    var rpc = require('web.rpc');

    var models = exports.PosModel.prototype.models;

    models.push(
        {
            model:  'l10n_co_edi_jorels.type_regimes',
            fields: ['name'],
            loaded: function(self, type_regimes) {
                self.type_regimes = type_regimes;
            }
        },
        {
            model:  'l10n_co_edi_jorels.type_liabilities',
            fields: ['name'],
            loaded: function(self, type_liabilities) {
                self.type_liabilities = type_liabilities;
            }
        },
        {
            model:  'l10n_co_edi_jorels.municipalities',
            fields: ['name'],
            loaded: function(self, municipalities) {
                self.municipalities = municipalities;
            }
        },
        {
            model:  'l10n_latam.identification.type',
            fields: ['name', 'l10n_co_document_code'],
            loaded: function(self, l10n_latam_identification_types) {
                self.l10n_latam_identification_types = l10n_latam_identification_types;
            }
        }
    );

    exports.load_fields('res.partner', [
        'company_type',
        'l10n_latam_identification_type_id',
        'type_regime_id',
        'type_liability_id',
        'municipality_id',
        'email_edi',
    ]);
    exports.load_fields('res.company', ['municipality_id', 'city']);

    exports.Order = exports.Order.extend({
        initialize: function(attributes,options){
            OrderSuper.prototype.initialize.call(this, attributes, options);
            this.to_electronic_invoice = false;
        },
        init_from_JSON: function(json) {
            OrderSuper.prototype.init_from_JSON.call(this, json);
            this.to_electronic_invoice = false;
            if (this.account_move){
                this.invoice = this.get_invoice();
                this.invoice.then(invoice => this.invoice = invoice);
            }
        },
        export_as_JSON: function() {
            var json = OrderSuper.prototype.export_as_JSON.call(this);
            json.to_electronic_invoice = this.to_electronic_invoice ? this.to_electronic_invoice : false;
            return json;
        },
        export_for_printing: function() {
            var receipt = OrderSuper.prototype.export_for_printing.call(this);
            if (this.invoice){
                receipt.invoice = this.invoice;
            }
            return receipt;
        },
        set_invoice: function(invoice) {
            this.invoice = invoice;
        },
        get_invoice: function() {
            self = this;
            return rpc.query({
                model: 'pos.order',
                method: 'get_invoice',
                args: [self.backendId],
            }).then(function(invoice){
                return invoice;
            });
        },
        set_to_electronic_invoice: function(to_electronic_invoice) {
            this.assert_editable();
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function(){
            return this.to_electronic_invoice;
        }
    });
});