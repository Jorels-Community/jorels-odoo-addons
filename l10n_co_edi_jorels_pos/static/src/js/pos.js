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

odoo.define('l10n_co_edi_jorels_pos', function(require) {
    "use strict";

    var PosDB = require('point_of_sale.DB');
    var core = require('web.core');
    var exports = require('point_of_sale.models');
    var gui = require('point_of_sale.gui');
    var screens = require('point_of_sale.screens');
    var _t = core._t;
    var rpc = require('web.rpc');

    var models = exports.PosModel.prototype.models;

    var partner_fields = [
        'company_type',
        'l10n_co_document_type',
        'type_regime_id',
        'type_liability_id',
        'municipality_id',
        'email_edi'
    ];

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
    );

    var set_fields_to_model = function(fields, models) {
        for(var i = 0; i < models.length; i++) {
            if(models[i].model == 'res.partner') {
                var model = models[i];
                for(var j = 0; j < fields.length; j++){
                    model.fields.push(fields[j]);
                }
                var old_domain = model.domain;
                model.domain = function(self) {
                    if (old_domain){
                        return ['|', old_domain[0], ['id','=',self.company.partner_id[0]]];
                    }
                    else{
                        return [['id','=',self.company.partner_id[0]]];
                    }
                }

                var old_loaded = model.loaded;
                model.loaded = function(self, partners) {
                    for(var i = 0; i < partners.length; i++) {
                        if(partners[i].id == self.company.partner_id[0]) {
                            var company_partner = partners.splice(i, 1);
                            self.company_partner = company_partner;
                        }
                    }
                    old_loaded(self, partners);
                }
            }
        }
    }

    set_fields_to_model(partner_fields, models);

    screens.ClientListScreenWidget.include({
        show: function() {
            var self = this;
            this._super();

            rpc.query({
                model: 'res.partner',
                method: 'search_read',
                args: [[['id','=',self.pos.company['id']]],['municipality_id']]
            })
            .then(function(partner_read){
                self.$('.new-customer').click(function(){
                    self.display_client_details('edit',{
                        'country_id': self.pos.company.country_id,
                        'state_id': self.pos.company.state_id,
                        'vat': '222222222222',
                        'company_type': 'person',
                        'l10n_co_document_type': 'national_citizen_id',
                        'type_regime_id': [2],
                        'type_liability_id': [29],
                        'municipality_id': [partner_read[0]['municipality_id'][0]]
                    });
                });
            });
        },
    });

    screens.PaymentScreenWidget.include({
        finalize_validation: function() {
            var self = this;
            var order = this.pos.get_order();

            if ((order.is_paid_with_cash() || order.get_change()) && this.pos.config.iface_cashdrawer) {

                    this.pos.proxy.printer.open_cashbox();
            }

            order.initialize_validation_date();
            order.finalized = true;

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.catch(this._handleFailedPushForInvoice.bind(this, order, false));

                invoiced.then(function (server_ids) {
                    self.invoicing = false;
                    var post_push_promise = [];
                    post_push_promise = self.post_push_order_resolve(order, server_ids);
                    post_push_promise.then(function () {
                        rpc.query({
                            model: 'pos.order',
                            method: 'get_invoice',
                            args: [server_ids],
                        })
                        .then(function (invoice) {
                            var order = self.pos.get_order();
                            order.invoice = invoice;
                            self.gui.show_screen('receipt');
                        });
                    }).catch(function (error) {
                        self.gui.show_screen('receipt');
                        if (error) {
                            self.gui.show_popup('error',{
                                'title': "Error: no internet connection",
                                'body':  error,
                            });
                        }
                    });
                });
            } else {
                var ordered = this.pos.push_order(order);
                if (order.wait_for_push_order()){
                    var server_ids = [];
                    ordered.then(function (ids) {
                      server_ids = ids;
                    }).finally(function() {
                        var post_push_promise = [];
                        post_push_promise = self.post_push_order_resolve(order, server_ids);
                        post_push_promise.then(function () {
                                self.gui.show_screen('receipt');
                            }).catch(function (error) {
                              self.gui.show_screen('receipt');
                              if (error) {
                                  self.gui.show_popup('error',{
                                      'title': "Error: no internet connection",
                                      'body':  error,
                                  });
                              }
                            });
                      });
                }
                else {
                  self.gui.show_screen('receipt');
                }
            }
        },
        click_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_invoice(!order.is_to_invoice());
            if (order.is_to_invoice()) {
                this.$('.js_invoice').addClass('highlight');
                this.$('.js_electronic_invoice').removeClass('hidden');
            } else {
                this.$('.js_invoice').removeClass('highlight');
                this.$('.js_electronic_invoice').addClass('hidden');
            }
        },
        click_electronic_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_electronic_invoice(!order.is_to_electronic_invoice());
            if (order.is_to_electronic_invoice()) {
                this.$('.js_electronic_invoice').addClass('highlight');
            } else {
                this.$('.js_electronic_invoice').removeClass('highlight');
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.js_electronic_invoice').click(function(){
                self.click_electronic_invoice();
            });
        },
    });

    exports.PosModel = exports.PosModel.extend({
        set_to_electronic_invoice: function(to_electronic_invoice) {
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function(){
            return this.to_electronic_invoice;
        },
    });

    exports.Order = exports.Order.extend({
        /**
         * Initialize PoS order from a JSON string.
         *
         * If the order was created in another session, the sequence number should be changed so it doesn't conflict
         * with orders in the current session.
         * Else, the sequence number of the session should follow on the sequence number of the loaded order.
         *
         * @param {object} json JSON representing one PoS order.
         */
        init_from_JSON: function(json) {
            var client;
            if (json.pos_session_id !== this.pos.pos_session.id) {
                this.sequence_number = this.pos.pos_session.sequence_number++;
            } else {
                this.sequence_number = json.sequence_number;
                this.pos.pos_session.sequence_number = Math.max(this.sequence_number+1,this.pos.pos_session.sequence_number);
            }
            this.session_id = this.pos.pos_session.id;
            this.uid = json.uid;
            this.name = _.str.sprintf(_t("Order %s"), this.uid);
            this.validation_date = json.creation_date;
            this.server_id = json.server_id ? json.server_id : false;
            this.user_id = json.user_id;

            if (json.fiscal_position_id) {
                var fiscal_position = _.find(this.pos.fiscal_positions, function (fp) {
                    return fp.id === json.fiscal_position_id;
                });

                if (fiscal_position) {
                    this.fiscal_position = fiscal_position;
                } else {
                    console.error('ERROR: trying to load a fiscal position not available in the pos');
                }
            }

            if (json.pricelist_id) {
                this.pricelist = _.find(this.pos.pricelists, function (pricelist) {
                    return pricelist.id === json.pricelist_id;
                });
            } else {
                this.pricelist = this.pos.default_pricelist;
            }

            if (json.partner_id) {
                client = this.pos.db.get_partner_by_id(json.partner_id);
                if (!client) {
                    console.error('ERROR: trying to load a partner not available in the pos');
                }
            } else {
                client = null;
            }
            this.set_client(client);

            this.temporary = false;     // FIXME
            this.to_invoice = false;    // FIXME
            this.to_electronic_invoice = false;    // FIXME

            var orderlines = json.lines;
            for (var i = 0; i < orderlines.length; i++) {
                var orderline = orderlines[i][2];
                this.add_orderline(new exports.Orderline({}, {pos: this.pos, order: this, json: orderline}));
            }

            var paymentlines = json.statement_ids;
            for (var i = 0; i < paymentlines.length; i++) {
                var paymentline = paymentlines[i][2];
                var newpaymentline = new exports.Paymentline({},{pos: this.pos, order: this, json: paymentline});
                this.paymentlines.add(newpaymentline);

                if (i === paymentlines.length - 1) {
                    this.select_paymentline(newpaymentline);
                }
            }
        },
        export_as_JSON: function() {
            var orderLines, paymentLines;
            orderLines = [];
            this.orderlines.each(_.bind( function(item) {
                return orderLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            paymentLines = [];
            this.paymentlines.each(_.bind( function(item) {
                return paymentLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            var json = {
                name: this.get_name(),
                amount_paid: this.get_total_paid() - this.get_change(),
                amount_total: this.get_total_with_tax(),
                amount_tax: this.get_total_tax(),
                amount_return: this.get_change(),
                lines: orderLines,
                statement_ids: paymentLines,
                pos_session_id: this.pos_session_id,
                pricelist_id: this.pricelist ? this.pricelist.id : false,
                partner_id: this.get_client() ? this.get_client().id : false,
                user_id: this.pos.user.id,
                employee_id: this.pos.get_cashier().id,
                uid: this.uid,
                sequence_number: this.sequence_number,
                creation_date: this.validation_date || this.creation_date, // todo: rename creation_date in master
                fiscal_position_id: this.fiscal_position ? this.fiscal_position.id : false,
                server_id: this.server_id ? this.server_id : false,
                to_invoice: this.to_invoice ? this.to_invoice : false,
                to_electronic_invoice: this.to_electronic_invoice ? this.to_electronic_invoice : false,
            };
            if (!this.is_paid && this.user_id) {
                json.user_id = this.user_id;
            }
            return json;
        },
        set_to_electronic_invoice: function(to_electronic_invoice) {
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function(){
            return this.to_electronic_invoice;
        },
    });

    screens.ReceiptScreenWidget.include({
		show: function () {
			this._super();
			var order = this.pos.get_order();
			if (order.invoice && order.invoice.ei_qr_data && order.invoice.ei_is_valid){
				new QRCode(document.getElementById("ei_qr_data") , {
					text: String(order.invoice.ei_qr_data),
					width: 100,
					height: 100
				});
			}
		},
	});

});
