# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of l10n_co_edi_jorels.
#
# l10n_co_edi_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import base64
import json
import logging
import math
import re
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import qrcode
import requests
from num2words import num2words
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
    _description = "Electronic invoicing"

    state = fields.Selection(selection_add=[('validate', 'Validating DIAN')], ondelete={'validate': 'set default'})
    number_formatted = fields.Char(string="Number formatted", compute="compute_number_formatted", store=True,
                                   copy=False)

    ei_type_document_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_documents', string="Edi Document type",
                                          copy=False, ondelete='RESTRICT',
                                          compute='_compute_ei_type_document', store=True,
                                          default=lambda self: self._compute_ei_type_document())
    ei_type_document = fields.Selection(selection=[
        ('none', 'None'),
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit note'),
        ('debit_note', 'Debit note'),
        ('doc_support', 'Document support'),
        ('note_support', 'Note support'),
    ], string="Document type", copy=False, compute='_compute_ei_type_document', store=True,
        default=lambda self: self._compute_ei_type_document())

    ei_customer = fields.Text(string="customer json", copy=False)
    ei_legal_monetary_totals = fields.Text(string="legal_monetary_totals json", copy=False)
    ei_invoice_lines = fields.Text(string="invoice_lines json", copy=False)

    # They allow to store synchronous and production modes used when invoicing
    ei_sync = fields.Boolean(string="Sync", default=False, copy=False, readonly=True)
    ei_is_not_test = fields.Boolean(string="In production", copy=False, readonly=True,
                                    default=lambda self: self.env.company.is_not_test,
                                    store=True, compute="_compute_ei_is_not_test")

    # API Response:
    ei_is_valid = fields.Boolean(string="Valid", copy=False)
    ei_is_restored = fields.Boolean("Is restored?", copy=False, readonly=True)
    ei_algorithm = fields.Char(string="Algorithm", copy=False, readonly=True)
    ei_class = fields.Char("Class", copy=False, readonly=True)
    ei_number = fields.Char(string="Edi number", compute="compute_number_formatted", store=True, copy=False,
                            readonly=True)
    ei_uuid = fields.Char(string="UUID", copy=False)
    ei_issue_date = fields.Date(string="Issue date", copy=False)
    ei_issue_datetime = fields.Char(string="Issue datetime", copy=False, readonly=True)
    ei_expedition_date = fields.Char("Expedition date", copy=False, readonly=True)
    ei_zip_key = fields.Char(string="Zip key", copy=False)
    ei_status_code = fields.Char(string="Status code", copy=False, readonly=True)
    ei_status_description = fields.Char(string="Status description", copy=False, readonly=True)
    ei_status_message = fields.Char(string="Status message", copy=False, readonly=True)
    ei_errors_messages = fields.Text("Message", copy=False, readonly=True)
    ei_xml_name = fields.Char(string="Xml name", copy=False, readonly=True)
    ei_zip_name = fields.Char(string="Zip name", copy=False, readonly=True)
    ei_signature = fields.Char(string="Signature", copy=False, readonly=True)
    ei_qr_code = fields.Char("QR code", copy=False, readonly=True)
    ei_qr_data = fields.Text(string="QR data", copy=False, readonly=True)
    ei_qr_link = fields.Char("QR link", copy=False, readonly=True)
    ei_pdf_download_link = fields.Char("PDF link", copy=False, readonly=True)
    ei_xml_base64_bytes = fields.Binary('XML', attachment=True, copy=False, readonly=True)
    ei_application_response_base64_bytes = fields.Binary("Application response", attachment=True, copy=False,
                                                         readonly=True)
    ei_attached_document_base64_bytes = fields.Binary("Attached document", attachment=True, copy=False)
    ei_pdf_base64_bytes = fields.Binary('Pdf document', attachment=True, copy=False)
    ei_zip_base64_bytes = fields.Binary('Zip document', attachment=True, copy=False, readonly=True)
    ei_type_environment = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_environments",
                                          string="Type environment", copy=False,
                                          default=lambda self: self._default_ei_type_environment())
    ei_payload = fields.Text("Payload", copy=False, readonly=True)

    # Old fields, compatibility
    ei_xml_file_name = fields.Char(string="Xml file name", copy=False, readonly=True)
    ei_url_acceptance = fields.Char(string="URL acceptance", copy=False, readonly=True)
    ei_url_rejection = fields.Char(string="URL rejection", copy=False, readonly=True)
    ei_xml_bytes = fields.Boolean(string="XML Bytes", copy=False, readonly=True)
    ei_dian_response_base64_bytes = fields.Binary('DIAN response', attachment=True, copy=False, readonly=True)

    # For mail attached
    ei_attached_zip_base64_bytes = fields.Binary('Attached zip', attachment=True, copy=False)

    # Additional documents for electronic invoicing
    ei_additional_documents = fields.Many2many('ir.attachment', string='Additional Documents',
                                               help='Additional documents to be attached to the electronic invoicing email')

    # QR image
    ei_qr_image = fields.Binary("QR image", attachment=True, copy=False, readonly=True)

    # Total taxes only / without withholdings
    ei_amount_tax_withholding = fields.Monetary("Withholdings", compute="_compute_amount", store=True)
    ei_amount_tax_withholding_company = fields.Monetary("Withholdings in Company Currency", compute="_compute_amount",
                                                        store=True, currency_field='company_currency_id')
    ei_amount_tax_no_withholding = fields.Monetary("Taxes without withholdings", compute="_compute_amount", store=True)
    ei_amount_tax_no_withholding_company = fields.Monetary("Taxes without withholdings in Company Currency",
                                                           compute="_compute_amount", store=True,
                                                           currency_field='company_currency_id')
    ei_amount_total_no_withholding = fields.Monetary("Total without withholdings", compute="_compute_amount",
                                                     store=True)
    ei_amount_total_no_withholding_company = fields.Monetary("Total without withholdings in Company Currency",
                                                             compute="_compute_amount", store=True,
                                                             currency_field='company_currency_id')

    # Total base excluding tax
    ei_amount_excluded = fields.Monetary("Excluded", compute="_compute_amount", store=True)
    ei_amount_excluded_company = fields.Monetary("Excluded in Company Currency", compute="_compute_amount", store=True,
                                                 currency_field='company_currency_id')

    # Commercial sample
    ei_amount_commercial_sample = fields.Monetary("Total commercial sample", compute="_compute_amount", store=True)
    ei_amount_commercial_sample_company = fields.Monetary("Total commercial sample in Company Currency",
                                                          compute="_compute_amount", store=True,
                                                          currency_field='company_currency_id')

    # Required field for credit and debit notes in DIAN
    ei_correction_concept_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                               string="Correction concept", copy=False, readonly=True,
                                               compute="compute_ei_correction_concept_id", store=True,
                                               ondelete='RESTRICT')
    ei_correction_concept_credit_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                                      string="Credit correction concept", copy=False,
                                                      domain=[('type_document_id', 'in', (5, 13))],
                                                      ondelete='RESTRICT')
    ei_correction_concept_debit_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.correction_concepts',
                                                     string="Debit correction concept", copy=False,
                                                     domain=[('type_document_id', '=', '6')], ondelete='RESTRICT')
    ei_is_correction_without_reference = fields.Boolean("Is it a correction without reference?", default=False)

    value_letters = fields.Char("Value in letters", compute="_compute_amount", store=True)

    is_attached_document_matched = fields.Boolean("Correct number in attached document?", copy=False,
                                                  compute='_is_attached_document_matched', store=True)
    ei_operation = fields.Selection([
        ('aiu', 'AIU'),
        ('standard', 'Standard'),
        ('mandates', 'Mandates'),
        ('transport', 'Transport'),
        ('exchange', 'Exchange'),
        ('iva_free_day', 'Día Sin IVA (No activo)')
    ], string="Operation type", default=lambda self: self.env.company.ei_operation, copy=True,
        required=True)

    # Period
    date_start = fields.Date(string="Start date", default=None, copy=True)
    date_end = fields.Date(string="End date", default=None, copy=True)

    # Order Reference
    order_ref_number = fields.Char(string="Order reference", default=None, copy=False)
    order_ref_date = fields.Date(string="Order date", default=None, copy=False)

    # Is out of country
    is_out_country = fields.Boolean(string='Is it for out of the country?',
                                    default=lambda self: self.get_default_is_out_country())

    # Payment form
    payment_form_id = fields.Many2one(string="Payment form", comodel_name='l10n_co_edi_jorels.payment_forms',
                                      copy=True, store=True, compute="_compute_payment_form_id",
                                      readonly=True, ondelete='RESTRICT')
    payment_method_id = fields.Many2one(string="Payment method", comodel_name='l10n_co_edi_jorels.payment_methods',
                                        default=lambda self: self._default_payment_method_id(), copy=True,
                                        domain=[('scope', '=', False)], ondelete='RESTRICT')

    # Store resolution
    resolution_id = fields.Many2one(string="Resolution", comodel_name='l10n_co_edi_jorels.resolution', copy=False,
                                    store=True, compute="_compute_resolution", ondelete='RESTRICT')

    radian_ids = fields.One2many(comodel_name='l10n_co_edi_jorels.radian', inverse_name='move_id')

    is_edi_mail_sent = fields.Boolean(readonly=True, default=False, copy=False,
                                      help="It indicates that the edi document has been sent.")

    # === Amount fields in company currency ===
    is_multicurrency = fields.Boolean(string='Is multicurrency?', compute='_compute_is_multicurrency')

    def _auto_init(self):
        # Edi type document
        if not column_exists(self.env.cr, "account_move", "ei_type_document_id"):
            create_column(self.env.cr, "account_move", "ei_type_document_id", "integer")

        if not column_exists(self.env.cr, "account_move", "ei_type_document"):
            create_column(self.env.cr, "account_move", "ei_type_document", "varchar")

        # Totals in Invoice Currency
        if not column_exists(self.env.cr, "account_move", "ei_amount_tax_withholding"):
            create_column(self.env.cr, "account_move", "ei_amount_tax_withholding", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_tax_no_withholding"):
            create_column(self.env.cr, "account_move", "ei_amount_tax_no_withholding", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_total_no_withholding"):
            create_column(self.env.cr, "account_move", "ei_amount_total_no_withholding", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_excluded"):
            create_column(self.env.cr, "account_move", "ei_amount_excluded", "numeric")

        # Totals in Company Currency
        if not column_exists(self.env.cr, "account_move", "ei_amount_tax_withholding_company"):
            create_column(self.env.cr, "account_move", "ei_amount_tax_withholding_company", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_tax_no_withholding_company"):
            create_column(self.env.cr, "account_move", "ei_amount_tax_no_withholding_company", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_total_no_withholding_company"):
            create_column(self.env.cr, "account_move", "ei_amount_total_no_withholding_company", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_excluded_company"):
            create_column(self.env.cr, "account_move", "ei_amount_excluded_company", "numeric")

        # Commercial samples
        if not column_exists(self.env.cr, "account_move", "ei_amount_commercial_sample"):
            create_column(self.env.cr, "account_move", "ei_amount_commercial_sample", "numeric")

        if not column_exists(self.env.cr, "account_move", "ei_amount_commercial_sample_company"):
            create_column(self.env.cr, "account_move", "ei_amount_commercial_sample_company", "numeric")

        # Value letters
        if not column_exists(self.env.cr, "account_move", "value_letters"):
            create_column(self.env.cr, "account_move", "value_letters", "varchar")

        return super()._auto_init()

    def dian_preview(self):
        for rec in self:
            if rec.ei_uuid:
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey=' + rec.ei_uuid,
                }

    def dian_pdf_view(self):
        for rec in self:
            if rec.ei_uuid:
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://catalogo-vpfe.dian.gov.co/Document/DownloadPDF?trackId=' + rec.ei_uuid,
                }

    def is_to_send_edi_email(self):
        self.ensure_one()
        return self.ei_is_valid \
            and self.move_type in ('out_invoice', 'out_refund') \
            and self.state not in ('draft', 'validate') \
            and bool(self.ei_uuid) \
            and bool(self.ei_attached_document_base64_bytes)

    def _send_edi_email(self):
        for rec in self:
            mail_template = rec.env.ref('l10n_co_edi_jorels.email_template_edi', False)
            ctx = dict(
                active_model='account.move',
                no_new_invoice=True,
                mail_notify_force_send=True
            )
            if mail_template and rec.is_to_send_edi_email():
                rec.with_context(ctx).message_post_with_source(
                    mail_template,
                    email_layout_xmlid="mail.mail_notification_light",
                    subtype_xmlid='mail.mt_comment',
                )
        return True

    def _default_ei_type_environment(self):
        if not self.env['l10n_co_edi_jorels.type_environments'].search_count([]):
            self.env['res.company'].init_csv_data('l10n_co_edi_jorels.l10n_co_edi_jorels.type_environments')
        return 1 if self.env.company.is_not_test else 2

    @api.depends("ei_type_environment")
    def _compute_ei_is_not_test(self):
        for rec in self:
            if rec.ei_type_environment:
                rec.ei_is_not_test = (rec.ei_type_environment.id == 1)
            else:
                rec.ei_is_not_test = rec.company_id.is_not_test

    def _default_payment_method_id(self):
        if not self.env['l10n_co_edi_jorels.payment_methods'].search_count([]):
            self.env['res.company'].init_csv_data('l10n_co_edi_jorels.l10n_co_edi_jorels.payment_methods')
        return 1

    @api.depends('invoice_date', 'invoice_date_due')
    def _compute_payment_form_id(self):
        if not self.env['l10n_co_edi_jorels.payment_forms'].search_count([]):
            self.env['res.company'].init_csv_data('l10n_co_edi_jorels.l10n_co_edi_jorels.payment_forms')

        for rec in self:
            if rec.invoice_date and rec.invoice_date_due:
                if rec.invoice_date >= rec.invoice_date_due:
                    # Cash
                    rec.payment_form_id = 1
                else:
                    # Credit
                    rec.payment_form_id = 2
            else:
                # Cash
                rec.payment_form_id = 1

    def get_default_is_out_country(self):
        for rec in self:
            return bool(rec.journal_id.is_out_country)

    @api.onchange('journal_id')
    def _onchange_is_out_country(self):
        for rec in self:
            rec.is_out_country = rec.get_default_is_out_country()

    def is_journal_pos(self):
        self.ensure_one()
        # POS invoices are now always made as electronic invoices, not as POS equivalent documents
        # therefore, the journal will always be treated as if it's not an electronic POS journal
        return False

    @api.model
    def is_universal_discount(self):
        try:
            if 'ks_amount_discount' in self:
                return bool(self.env['res.company'].search([('ks_enable_discount', '=', True)]))
            else:
                return False
        except KeyError:
            return False

    def write_response(self, response, payload):
        try:
            for rec in self:
                rec.ei_is_valid = response['is_valid']
                rec.ei_is_restored = response['is_restored']
                rec.ei_algorithm = response['algorithm']
                rec.ei_class = response['class']
                rec.ei_uuid = response['uuid']
                rec.ei_issue_date = response['issue_date']
                rec.ei_issue_datetime = response['issue_date']
                rec.ei_expedition_date = response['expedition_date']
                rec.ei_zip_key = response['zip_key']
                rec.ei_status_code = response['status_code']
                rec.ei_status_description = response['status_description']
                rec.ei_status_message = response['status_message']
                rec.ei_errors_messages = str(response['errors_messages'])
                rec.ei_xml_name = response['xml_name']
                rec.ei_zip_name = response['zip_name']
                rec.ei_signature = response['signature']
                rec.ei_qr_code = response['qr_code']
                rec.ei_qr_data = response['qr_data']
                rec.ei_qr_link = response['qr_link']
                rec.ei_pdf_download_link = response['pdf_download_link']
                rec.ei_xml_base64_bytes = response['xml_base64_bytes']
                rec.ei_application_response_base64_bytes = response['application_response_base64_bytes']
                rec.ei_attached_document_base64_bytes = response['attached_document_base64_bytes']
                rec.ei_pdf_base64_bytes = response['pdf_base64_bytes']
                rec.ei_zip_base64_bytes = response['zip_base64_bytes']
                rec.ei_type_environment = response['type_environment_id']
                rec.ei_payload = payload

                # QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=2,
                    border=2,
                )
                qr.add_data(rec.ei_qr_data)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.ei_qr_image = qr_image
        except Exception as e:
            _logger.debug("Write response: %s", e)

    def get_type_document_identification_id(self):
        for rec in self:
            if rec.partner_id.type == 'invoice' and rec.partner_id.parent_id:
                rec_partner = rec.partner_id.parent_id
            else:
                rec_partner = rec.partner_id

            return rec_partner.type_document_identification_id.id

    def get_ei_customer(self):
        for rec in self:
            if rec.partner_id.type == 'invoice' and rec.partner_id.parent_id:
                rec_partner = rec.partner_id.parent_id

                if rec.partner_id.email:
                    email_edi = rec.partner_id.email
                else:
                    raise UserError(_("The client must have an email where to send the invoice."))
            else:
                rec_partner = rec.partner_id

                if rec_partner.email_edi:
                    email_edi = rec_partner.email_edi
                elif rec.company_id.ei_ignore_edi_email_check and rec_partner.email:
                    email_edi = rec_partner.email
                else:
                    raise UserError(_("The client must have an email where to send the invoice."))

            type_document_identification_id = rec.get_type_document_identification_id()
            if type_document_identification_id:
                if rec.partner_id.vat:
                    if type_document_identification_id in (1, 2, 3, 4, 5, 6, 10, 24, 38):
                        identification_number_general = ''.join([i for i in rec.partner_id.vat if i.isdigit()])
                    else:
                        identification_number_general = rec.partner_id.vat

                    # If it is Nit remove the check digit
                    if type_document_identification_id == 6:
                        identification_number = identification_number_general[:-1]
                    else:
                        identification_number = identification_number_general

                    if identification_number:
                        name = rec_partner.name

                        type_organization_id = 1 if rec_partner.is_company else 2

                        if rec_partner.merchant_registration:
                            merchant_registration = rec_partner.merchant_registration
                        else:
                            merchant_registration = 'No tiene'

                        customer_data = {
                            "id_code": type_document_identification_id,
                            "id_number": identification_number,
                            "organization_code": type_organization_id,
                            "name": name,
                            "email": email_edi,
                            "merchant_registration": merchant_registration
                        }

                        if rec_partner.trade_name:
                            customer_data['trade_name'] = rec_partner.trade_name

                        if rec_partner.country_id:
                            customer_rec = self.env['l10n_co_edi_jorels.countries'].search(
                                [('code', '=', rec_partner.country_id.code)]
                            )
                            if customer_rec:
                                customer_data['country_code'] = customer_rec.id
                            else:
                                raise UserError(_("You must assign the client a valid country"))
                        else:
                            raise UserError(_("You must assign the client a country"))

                        if rec_partner.country_id.code == 'CO':
                            if rec.is_out_country:
                                raise UserError(_("This is an export invoice but the client's country is Colombia"))

                            if rec_partner.municipality_id:
                                customer_data['municipality_code'] = rec_partner.municipality_id.id
                            elif rec_partner.postal_municipality_id:
                                municipality_rec = self.env['l10n_co_edi_jorels.municipalities'].search(
                                    [('code', '=', rec_partner.postal_municipality_id.code)])
                                customer_data['municipality_code'] = municipality_rec.id
                            else:
                                raise UserError(_("You must assign the client a municipality"))

                        if rec_partner.type_regime_id:
                            customer_data['regime_code'] = rec_partner.type_regime_id.id
                        else:
                            raise UserError(_("You must assign the client a type of regimen"))

                        if rec_partner.type_liability_id:
                            customer_data['liability_code'] = rec_partner.type_liability_id.id
                        else:
                            raise UserError(_("You must assign the customer a type of liability"))

                        if rec.partner_id.phone:
                            phone = rec.partner_id.phone
                            if phone[:3] == '+57':
                                temp_phone = ''.join([i for i in phone[3:] if i.isdigit()])
                                phone = temp_phone
                            if phone:
                                customer_data['phone'] = phone

                        if rec.partner_id.street:
                            address = rec.partner_id.street.split(',')[0]
                            if address:
                                customer_data['address'] = address

                        return customer_data
                else:
                    raise UserError(_("The client does not have an identification document number."))
            else:
                raise UserError(_("The client does not have an associated identification document type."))
        return False

    def get_ei_legal_monetary_totals(self):
        self.ensure_one()
        line_extension_amount = abs(self.amount_untaxed_signed)
        tax_exclusive_amount = abs(
            self.amount_untaxed_signed) - self.ei_amount_excluded_company + self.ei_amount_commercial_sample_company

        allowance_total_amount = 0.0
        if self.is_universal_discount():
            if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                raise UserError(
                    _("The universal discount module doesn't seem to be compatible with multi-currencies."))

            allowance_total_amount = self.ks_amount_discount

        charge_total_amount = 0.0
        payable_amount = self.ei_amount_total_no_withholding_company
        tax_inclusive_amount = payable_amount - charge_total_amount + allowance_total_amount

        return {
            "line_extension_value": line_extension_amount,
            "tax_exclusive_value": tax_exclusive_amount,
            "tax_inclusive_value": tax_inclusive_amount,
            "payable_value": payable_amount
        }

    def get_ei_lines(self):
        self.ensure_one()

        lines = []
        round_curr = self.company_currency_id.round
        for invoice_line_id in self.invoice_line_ids:
            if invoice_line_id.account_id:
                if not (0 <= invoice_line_id.discount < 100):
                    raise UserError(_("The discount must always be greater than or equal to 0 and less than 100."))

                price_unit = 100.0 * abs(invoice_line_id.balance) / (invoice_line_id.quantity * (
                        100.0 - invoice_line_id.discount))
                # The temporary dictionary of elements that belong to the specific line
                invoice_temps = {}
                products = {}
                allowance_charges = {}
                tax_totals = {'tax_totals': []}
                products.update({'price_value': price_unit})
                products.update({'base_quantity': invoice_line_id.quantity})

                if invoice_line_id.product_id.code:
                    products.update({'product_ref': invoice_line_id.product_id.code})
                else:
                    raise UserError(_("All products must have an internal reference assigned"))

                if self.is_out_country:
                    if invoice_line_id.product_id.brand_name:
                        products.update({'brand_name': invoice_line_id.product_id.brand_name})
                    else:
                        raise UserError(_("Products on export invoices must have a brand name"))

                    if invoice_line_id.product_id.model_name:
                        products.update({'model_name': invoice_line_id.product_id.model_name})
                    else:
                        raise UserError(_("Products on export invoices must have a model name"))

                products.update({'description': invoice_line_id.name})

                if invoice_line_id.ei_notes:
                    products.update({'notes': [{'text': invoice_line_id.ei_notes}]})

                if invoice_line_id.product_uom_id.edi_unit_measure_id.id:
                    products.update({'uom_code': invoice_line_id.product_uom_id.edi_unit_measure_id.id})
                else:
                    raise UserError(_("All products must be assigned a unit of measure (DIAN)"))

                products.update({'quantity': invoice_line_id.quantity})
                products.update({'line_extension_value': abs(invoice_line_id.balance)})
                # TODO: Standard product codes compatibility
                # [4]: Taxpayer adoption standard ('999')
                products.update({'item_code': 4})

                # Discounts
                if invoice_line_id.discount:
                    discount = True
                    allowance_charges.update({'indicator': False})
                    amount = round_curr(abs(invoice_line_id.balance) * invoice_line_id.discount / (
                            100.0 - invoice_line_id.discount))
                    base_amount = round_curr(abs(invoice_line_id.balance) + amount)
                    allowance_charge_reason = "Descuento"
                else:
                    discount = False
                    allowance_charges.update({'indicator': False})
                    amount = 0
                    base_amount = 0
                    allowance_charge_reason = ""

                taxable_amount_company = abs(invoice_line_id.balance)

                # If it is a commercial sample the taxable amount is zero and not discount but have lst_price
                commercial_sample = False
                if not taxable_amount_company and not discount and invoice_line_id.product_id.lst_price:
                    if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                        raise UserError(
                            _("Commercial samples doesn't seem to be compatible with multi-currencies."))

                    # Use the following code, as an example, to configure the tax for a commercial sample.
                    # For this you must install the account_tax_python module and
                    # select the "Tax computation" field as "Python code" in the tax form.
                    #
                    # In the "Python code" field, in the tax form; for 19% tax:
                    #
                    # if price_unit:
                    #     result = price_unit * quantity * 0.19
                    # else:
                    #     result = product.lst_price * quantity * 0.19
                    #
                    commercial_sample = True
                    products.update({'price_code': 1})  # Commercial value ('01')
                    taxable_amount_company = invoice_line_id.product_id.lst_price * invoice_line_id.quantity
                    products.update({'price_value': invoice_line_id.product_id.lst_price})

                allowance_charges.update({'base_value': base_amount})
                allowance_charges.update({'value': amount})
                allowance_charges.update({'reason': allowance_charge_reason})

                # Calculate tax totals for invoice line
                for invoice_line_tax_id in invoice_line_id.tax_ids:
                    tax_total = {}

                    if invoice_line_tax_id.edi_tax_id.id:
                        edi_tax_name = invoice_line_tax_id.edi_tax_id.name
                        tax_name = invoice_line_tax_id.description or ''
                        dian_report_tax_base = invoice_line_tax_id.dian_report_tax_base or 'auto'
                        # The information sent to DIAN should not include the withholdings
                        if edi_tax_name[:4] != 'Rete' \
                                and not tax_name.startswith(('IVA Excluido', 'IVA Compra Excluido')) \
                                and not (edi_tax_name == 'IVA' and dian_report_tax_base == 'no_report'):
                            if invoice_line_tax_id.amount_type == 'percent':
                                tax_total.update({'code': invoice_line_tax_id.edi_tax_id.id})
                                tax_total.update({'tax_value': round_curr(
                                    taxable_amount_company * invoice_line_tax_id.amount / 100.0)})
                                tax_total.update({'taxable_value': round_curr(taxable_amount_company)})
                                tax_total.update({'percent': invoice_line_tax_id.amount})
                                tax_totals['tax_totals'].append(tax_total)
                            elif invoice_line_tax_id.amount_type == 'fixed':
                                tax_total.update({'code': invoice_line_tax_id.edi_tax_id.id})
                                tax_total.update({'tax_value': round_curr(
                                    invoice_line_id.quantity * invoice_line_tax_id.amount)})
                                tax_total.update({'taxable_value': invoice_line_id.quantity})
                                # "886","number of international units","NIU"
                                tax_total.update({'uom_code': 886})
                                tax_total.update({'unit_value': round_curr(invoice_line_tax_id.amount)})
                                tax_total.update({'base_uom': "1.000000"})
                                tax_totals['tax_totals'].append(tax_total)
                            elif invoice_line_tax_id.amount_type == 'code':
                                # For now, only compatible with percentage taxes
                                if commercial_sample:
                                    tax_total.update({'code': invoice_line_tax_id.edi_tax_id.id})
                                    tax_total.update({'tax_value': round_curr(invoice_line_id.price_total)})
                                    tax_total.update({'taxable_value': round_curr(taxable_amount_company)})
                                    # The tax is rounded to 0 decimal places, integers. In case of rounding issues,
                                    # it is expected that this will be sufficient to correct the problem and at the
                                    # same time cover all possible percentage tax values for Colombia.
                                    tax_total.update({'percent': round(
                                        invoice_line_id.price_total / taxable_amount_company * 100)})
                                    tax_totals['tax_totals'].append(tax_total)
                                else:
                                    tax_total.update({'code': invoice_line_tax_id.edi_tax_id.id})
                                    tax_total.update({'tax_value': round_curr(
                                        taxable_amount_company * invoice_line_tax_id.amount / 100.0)})
                                    tax_total.update({'taxable_value': round_curr(taxable_amount_company)})
                                    tax_total.update({'percent': invoice_line_tax_id.amount})
                                    tax_totals['tax_totals'].append(tax_total)
                            else:
                                raise UserError(_("Electronic invoicing is not yet compatible with this tax type."))
                    else:
                        raise UserError(_("All taxes must be assigned a tax type (DIAN)."))

                # UPDATE ALL THE ELEMENTS OF THE PRODUCT
                invoice_temps.update(products)

                # UPDATE ALL PRODUCT DISCOUNTS (* ONLY ONE IS SUPPOSED *)
                if discount:
                    invoice_temps.update({'allowance_charges': [allowance_charges]})

                # Taxes are attached inside this json
                if tax_totals['tax_totals']:
                    invoice_temps.update({'tax_totals': tax_totals['tax_totals']})

                # Transport compatibility
                if self.ei_operation == 'transport':
                    if 'waypoint_id' not in invoice_line_id:
                        raise UserError(_("Transport compatibility is only available with "
                                          "Jorels SAS Freight Route Module"))

                    if invoice_line_id.waypoint_id:
                        # Check field values
                        if not invoice_line_id.waypoint_id.number:
                            raise UserError(_("A waypoint doesn't have an associated id number"))
                        if not invoice_line_id.waypoint_id.rndc_entry_code:
                            raise UserError(_("Waypoint doesn't have an rndc ingress id: %s")
                                            % invoice_line_id.waypoint_id.number)
                        if not invoice_line_id.waypoint_id.total:
                            raise UserError(_("The waypoint %s doesn't have an total")
                                            % invoice_line_id.waypoint_id.number)
                        if not invoice_line_id.waypoint_id.weight:
                            raise UserError(_("The waypoint %s doesn't have an weight")
                                            % invoice_line_id.waypoint_id.number)

                        # Transport remittance registered in the RNDC
                        invoice_temps.update({'sector_code': 2})

                        # 01. Remittance filing number provided by RNDC
                        # 02. Remittance consecutive number according the internal coding of each transport company.
                        # 03. Freight value to be charged for the transport service.
                        # "767","kilogram","KGM"
                        # "686","gallon","GLL"
                        item_properties = [{
                            'name': '01',
                            'value': invoice_line_id.waypoint_id.rndc_entry_code
                        }, {
                            'name': '02',
                            'value': invoice_line_id.waypoint_id.number
                        }, {
                            'name': '03',
                            'value': invoice_line_id.waypoint_id.total,
                            'uom_code': '767',
                            'quantity': invoice_line_id.waypoint_id.weight
                        }]
                        invoice_temps.update({'item_properties': item_properties})
                    else:
                        # Additional service
                        invoice_temps.update({'sector_code': 1})

                # Mandates compatibility
                if self.ei_operation == 'mandates':
                    raise UserError(_("Electronic invoicing does not yet support mandates"))

                # Exchange compatibility
                if self.ei_operation == 'exchange':
                    raise UserError(_("Electronic invoicing does not yet support exchange"))

                # Iva free day compatibility
                if self.ei_operation == 'iva_free_day':
                    raise UserError(_("Electronic invoicing does not yet support iva_free_day"))

                if self.ei_type_document_id.id == 12:
                    if self.invoice_date != fields.Date.context_today(self):
                        raise UserError(_("The issue date must be today's date"))
                    # Support document
                    # Form generation transmission (transmission code)
                    # 1, Por operación (Default)
                    # 2, Acumulado semanal
                    invoice_temps.update({
                        'period': {
                            'date': fields.Date.to_string(self.invoice_date),
                            'transmission_code': 1
                        }
                    })

                lines.append(invoice_temps)

        return lines

    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()

        for rec in self:
            amount_tax_withholding = 0
            amount_tax_no_withholding = 0
            amount_excluded = 0
            amount_commercial_sample = 0

            currency = rec.currency_id
            company = rec.company_id or self.env.company
            rate_date = rec.date or rec.invoice_date or fields.Date.context_today(self)
            rate = rec.currency_id.with_context(dict(rec._context or {}, date=rate_date)).rate
            inverse_rate = rec.currency_id.with_context(dict(rec._context or {}, date=rec.invoice_date)).inverse_rate
            for invoice_line_id in rec.invoice_line_ids:
                if invoice_line_id.account_id:
                    taxable_amount = invoice_line_id.price_subtotal
                    discount = bool(invoice_line_id.discount)

                    # If it is a commercial sample the taxable amount is zero and not discount but have lst_price
                    if not taxable_amount and not discount and invoice_line_id.product_id.lst_price:
                        # if rec.currency_id and rec.company_id and rec.currency_id != rec.company_id.currency_id:
                        #   raise UserError(
                        #       _("Commercial samples doesn't seem to be compatible with multi-currencies."))

                        lst_price_company = invoice_line_id.product_id.lst_price
                        lst_price_invoice = lst_price_company * rate

                        taxable_amount = lst_price_invoice * invoice_line_id.quantity

                        amount_commercial_sample = amount_commercial_sample + taxable_amount

                    for invoice_line_tax_id in invoice_line_id.tax_ids:
                        tax_name = invoice_line_tax_id.description or ''
                        dian_report_tax_base = invoice_line_tax_id.dian_report_tax_base or 'auto'

                        if invoice_line_tax_id.amount_type == 'fixed':
                            # For fixed amount type
                            # The 'amount' field automatically uses the value defined in the tax configuration
                            # without currency conversion.
                            tax_amount = invoice_line_id.quantity * invoice_line_tax_id.amount
                        else:
                            # For percent and code amount type
                            tax_amount = taxable_amount * invoice_line_tax_id.amount / 100.0

                        if invoice_line_tax_id.edi_tax_id.id:
                            edi_tax_name = invoice_line_tax_id.edi_tax_id.name
                            if tax_name.startswith(('IVA Excluido', 'IVA Compra Excluido')) or \
                                    (edi_tax_name == 'IVA' and dian_report_tax_base == 'no_report'):
                                amount_excluded = amount_excluded + taxable_amount
                            elif edi_tax_name[:4] == 'Rete':
                                amount_tax_withholding = amount_tax_withholding + tax_amount
                            else:
                                amount_tax_no_withholding = amount_tax_no_withholding + tax_amount
                        else:
                            if tax_name.startswith(('IVA Excluido', 'IVA Compra Excluido')) or \
                                    (tax_name.startswith('IVA') and dian_report_tax_base == 'no_report'):
                                amount_excluded = amount_excluded + taxable_amount
                            elif tax_name[:3] == 'Rte':
                                amount_tax_withholding = amount_tax_withholding + tax_amount
                            else:
                                amount_tax_no_withholding = amount_tax_no_withholding + tax_amount

            rec.ei_amount_tax_withholding = amount_tax_withholding
            rec.ei_amount_tax_withholding_company = currency._convert(rec.ei_amount_tax_withholding,
                                                                      company.currency_id, company, rate_date)
            rec.ei_amount_tax_no_withholding = amount_tax_no_withholding
            rec.ei_amount_tax_no_withholding_company = currency._convert(rec.ei_amount_tax_no_withholding,
                                                                         company.currency_id, company, rate_date)
            rec.ei_amount_total_no_withholding = rec.amount_untaxed + rec.ei_amount_tax_no_withholding
            rec.ei_amount_total_no_withholding_company = (abs(rec.amount_untaxed_signed) +
                                                          rec.ei_amount_tax_no_withholding_company)
            rec.ei_amount_excluded = amount_excluded
            rec.ei_amount_excluded_company = currency._convert(rec.ei_amount_excluded, company.currency_id, company,
                                                               rate_date)
            rec.ei_amount_commercial_sample = amount_commercial_sample
            rec.ei_amount_commercial_sample_company = currency._convert(rec.ei_amount_commercial_sample,
                                                                        company.currency_id, company, rate_date)

            if self.is_universal_discount():
                # if rec.currency_id and rec.company_id and rec.currency_id != rec.company_id.currency_id:
                #     raise UserError(
                #         _("The universal discount module doesn't seem to be compatible with multi-currencies."))

                if not ('ks_global_tax_rate' in rec):
                    rec.ks_calculate_discount()
                sign = rec.move_type in ['in_refund', 'out_refund'] and -1 or 1
                rec.amount_residual_signed = rec.amount_total * sign
                rec.amount_total_signed = rec.amount_total * sign

                rec.ei_amount_total_no_withholding = (rec.amount_untaxed +
                                                      rec.ei_amount_tax_no_withholding -
                                                      rec.ks_amount_discount)
                rec.ei_amount_total_no_withholding_company = (abs(rec.amount_untaxed_signed) +
                                                              rec.ei_amount_tax_no_withholding_company -
                                                              rec.ks_amount_discount)

            # Value in letters
            decimal_part, integer_part = math.modf(abs(rec.ei_amount_total_no_withholding_company))
            if decimal_part:
                decimal_part = round(decimal_part * math.pow(10, rec.company_currency_id.decimal_places))
            if integer_part:
                if rec.company_id.ei_enable:
                    lang = 'es_CO'
                else:
                    lang = rec.partner_id.lang if rec.partner_id.lang else 'en'

                rec.value_letters = (num2words(integer_part, lang=lang).upper() + ' ' +
                                     rec.company_currency_id.currency_unit_label.upper())
                if decimal_part:
                    rec.value_letters = (rec.value_letters + ', ' +
                                         num2words(decimal_part, lang=lang).upper() + ' ' +
                                         rec.company_currency_id.currency_subunit_label.upper() + '.')

    def get_ei_payment_form(self):
        for rec in self:
            if rec.invoice_date and rec.invoice_date_due:
                if rec.invoice_date >= rec.invoice_date_due:
                    # Cash
                    duration_measure = 0
                else:
                    # Credit
                    duration_measure = (rec.invoice_date_due - rec.invoice_date).days
                payment_due_date = fields.Date.to_string(rec.invoice_date_due)
            else:
                _logger.debug("The invoice or payment date is not valid")
                # Cash
                duration_measure = 0
                payment_due_date = fields.Date.to_string(rec.invoice_date)

            return {
                'code': rec.payment_form_id.id,
                'method_code': rec.payment_method_id.id,
                'due_date': payment_due_date,
                'duration_days': duration_measure
            }

    def should_send_document_to_dian(self):
        self.ensure_one()

        type_edi_document = self.ei_type_document

        if self.move_type in ('out_invoice', 'out_refund') and type_edi_document in (
                'invoice', 'credit_note', 'debit_note'):
            return True
        if self.move_type in ('in_invoice', 'in_refund') and type_edi_document in ('doc_support', 'note_support'):
            return True

        return False

    def is_pending_to_send_to_dian(self):
        self.ensure_one()

        if not self.company_id.ei_enable:
            return False
        if self.is_journal_pos():
            return False
        if self.ei_is_valid:
            return False

        return self.should_send_document_to_dian()

    @api.depends('is_out_country', 'ei_is_correction_without_reference', 'debit_origin_id', 'resolution_id',
                 'move_type')
    def _compute_ei_type_document(self):
        for rec in self:
            # Compute ei_type_document
            if rec.move_type == 'out_invoice':
                if (('debit_origin_id' in self) and rec.debit_origin_id) or rec.ei_is_correction_without_reference:
                    # Debit note
                    type_edi_document = 'debit_note'
                else:
                    # Sales invoice
                    type_edi_document = 'invoice'
            elif rec.move_type == 'out_refund':
                # Credit note
                type_edi_document = 'credit_note'
            elif rec.move_type == 'in_invoice' \
                    and rec.resolution_id \
                    and rec.resolution_id.resolution_type_document_id.id == 12:
                if (('debit_origin_id' in self) and rec.debit_origin_id) or rec.ei_is_correction_without_reference:
                    # There is no debit note for document support
                    raise UserError(_("There is not debit note for electronic document support"))
                else:
                    # Document support
                    type_edi_document = 'doc_support'
            elif rec.move_type == 'in_refund' \
                    and rec.resolution_id \
                    and rec.resolution_id.resolution_type_document_id.id == 13:
                # Note Document Support
                type_edi_document = 'note_support'
            elif rec.move_type == 'in_invoice':
                if (('debit_origin_id' in self) and rec.debit_origin_id) or rec.ei_is_correction_without_reference:
                    # Debit note
                    type_edi_document = 'debit_note'
                else:
                    # Sales invoice
                    type_edi_document = 'invoice'
            elif rec.move_type == 'in_refund':
                # Credit note
                type_edi_document = 'credit_note'
            else:
                type_edi_document = 'none'

            # Compute ei_type_document_id
            # For now the document type is always
            # Electronic invoicing (Code '01')
            # Export electronic invoicing (Code '02')
            # Credit note (Code '91')
            # Debit note (Code '92')
            # Support document (Code '05')
            # Credit note for support document (Code '95')
            # The contingency and others are pending review
            type_documents_env = self.env['l10n_co_edi_jorels.type_documents']
            if type_edi_document == 'invoice':
                # Sales invoice
                if not rec.is_out_country:
                    type_documents_rec = type_documents_env.search([('code', '=', '01')])
                else:
                    type_documents_rec = type_documents_env.search([('code', '=', '02')])
            elif type_edi_document == 'credit_note':
                # Credit note
                type_documents_rec = type_documents_env.search([('code', '=', '91')])
            elif type_edi_document == 'debit_note':
                # Debit note
                type_documents_rec = type_documents_env.search([('code', '=', '92')])
            elif type_edi_document == 'doc_support':
                # Document support
                type_documents_rec = type_documents_env.search([('code', '=', '05')])
            elif type_edi_document == 'note_support':
                # Note Document Support
                type_documents_rec = type_documents_env.search([('code', '=', '95')])
            else:
                type_documents_rec = None

            # Store compute fields
            rec.ei_type_document = type_edi_document
            rec.ei_type_document_id = type_documents_rec.id if type_documents_rec else None

    def get_ei_sync(self):
        self.ensure_one()
        self.ei_sync = self.ei_is_not_test
        return self.ei_sync

    def get_ei_is_not_test(self):
        self.ensure_one()
        return self.ei_is_not_test

    @api.depends('journal_id', 'ei_type_document')
    def _compute_resolution(self):
        for rec in self:
            type_edi_document = rec.ei_type_document
            if type_edi_document:
                if type_edi_document in ('invoice', 'doc_support') and rec.journal_id.resolution_invoice_id:
                    # Sales invoice
                    rec.resolution_id = rec.journal_id.resolution_invoice_id.id
                elif type_edi_document in (
                        'credit_note', 'note_support') and rec.journal_id.resolution_credit_note_id:
                    # Credit note
                    rec.resolution_id = rec.journal_id.resolution_credit_note_id.id
                elif type_edi_document == 'debit_note' and rec.journal_id.resolution_debit_note_id:
                    # Debit note
                    rec.resolution_id = rec.journal_id.resolution_debit_note_id.id
                else:
                    rec.resolution_id = None
            else:
                rec.resolution_id = None

    @api.depends('name', 'ref', 'journal_id')
    def compute_number_formatted(self):
        for rec in self:
            if rec.should_send_document_to_dian():
                prefix = rec.resolution_id.resolution_prefix
                ei_number = ''
                number_formatted = ''

                if rec.name and prefix:
                    # Remove non-alphanumeric characters
                    name = re.sub(r'\W+', '', rec.name)
                    len_prefix = len(prefix)
                    len_name = len(name)
                    if 0 < len_prefix < len_name and name[0:len_prefix] == prefix:
                        number_unformatted = ''.join([i for i in name[len_prefix:] if i.isdigit()])
                        if number_unformatted:
                            ei_number = str(int(number_unformatted))
                            number_formatted = prefix + ei_number

                if ei_number and number_formatted:
                    rec.ei_number = ei_number
                    rec.number_formatted = number_formatted
                else:
                    rec.ei_number = ''
                    rec.number_formatted = ''
                    _logger.debug('Compute number format: Error.')
            elif rec.move_type in ('in_invoice', 'in_refund'):
                rec.ei_number = rec.ref
                rec.number_formatted = rec.ref
            else:
                rec.ei_number = ''
                rec.number_formatted = ''

    @api.depends('ei_type_document_id', 'ei_correction_concept_credit_id', 'ei_correction_concept_debit_id')
    def compute_ei_correction_concept_id(self):
        for rec in self:
            type_document = rec.ei_type_document
            if type_document in ('credit_note', 'note_support'):
                rec.ei_correction_concept_id = rec.ei_correction_concept_credit_id.id
            elif type_document == 'debit_note':
                rec.ei_correction_concept_id = rec.ei_correction_concept_debit_id.id
            else:
                rec.ei_correction_concept_id = None

    def get_operation_code(self):
        self.ensure_one()
        operation = {
            'aiu': 9,
            'standard': 10,
            'mandates': 11,
            'transport': 12,
            'exchange': 25,
            'iva_free_day': 27
        }

        type_edi_document = self.ei_type_document
        if type_edi_document == 'credit_note':
            return 14 if self.ei_is_correction_without_reference else 13
        elif type_edi_document == 'debit_note':
            return 17 if self.ei_is_correction_without_reference else 16
        elif type_edi_document in ('doc_support', 'note_support'):
            return 28 if self.partner_id.tax_resident_co else 29
        else:
            return operation[self.ei_operation]

    def get_json_request(self, check_date=True):
        for rec in self:
            if rec.should_send_document_to_dian():
                # Important for compatibility with old fields,
                # third-party modules or manual changes to the database
                if not rec.ei_number or not rec.number_formatted:
                    rec.compute_number_formatted()

                # Check resolution
                if not rec.resolution_id:
                    raise UserError(
                        _("This type of document does not have a DIAN resolution assigned: %s") % rec.name)

                json_request = {
                    'number': rec.ei_number,
                    'type_document_code': rec.ei_type_document_id.id,
                    'sync': rec.get_ei_sync(),
                    'customer': rec.get_ei_customer(),
                    'operation_code': rec.get_operation_code()
                }

                if rec.ei_type_document == 'invoice':
                    json_request['resolution'] = {
                        'prefix': rec.resolution_id.resolution_prefix,
                        'resolution': rec.resolution_id.resolution_resolution,
                        'resolution_date': fields.Date.to_string(rec.resolution_id.resolution_resolution_date),
                        'technical_key': rec.resolution_id.resolution_technical_key,
                        'number_from': rec.resolution_id.resolution_from,
                        'number_to': rec.resolution_id.resolution_to,
                        'date_from': fields.Date.to_string(rec.resolution_id.resolution_date_from),
                        'date_to': fields.Date.to_string(rec.resolution_id.resolution_date_to)
                    }
                else:
                    json_request['resolution_code'] = rec.resolution_id.resolution_id

                # Due date
                if rec.invoice_date_due:
                    json_request['due_date'] = fields.Date.to_string(rec.invoice_date_due)

                # Issue date
                if rec.invoice_date:
                    if check_date and rec.invoice_date != fields.Date.context_today(rec):
                        raise UserError(_("The issue date must be today's date"))
                    json_request['date'] = fields.Date.to_string(rec.invoice_date)

                # Period
                if rec.date_start and rec.date_end:
                    json_request['period'] = {
                        'date_start': fields.Date.to_string(rec.date_start),
                        'date_end': fields.Date.to_string(rec.date_end)
                    }

                # Order reference
                if rec.order_ref_number:
                    json_request['order_reference'] = {
                        'number': rec.order_ref_number
                    }
                    if rec.order_ref_date:
                        json_request['order_reference']['issue_date'] = fields.Date.to_string(rec.order_ref_date)

                if not rec.company_id.currency_id or rec.company_id.currency_id.name != 'COP':
                    raise UserError(_('The company currency must be COP to report bills to DIAN. '
                                      'Set it up in the Companies configuration view in Odoo.'))

                # Multi-currency compatibility
                if rec.currency_id and rec.company_id and rec.currency_id != rec.company_id.currency_id:
                    company_currency_code = rec.company_id.currency_id.name
                    invoice_currency_code = rec.currency_id.name

                    if not rec.journal_id.currency_id or rec.journal_id.currency_id.name != 'COP':
                        raise UserError(_('The currency of their journal must be COP to report bills to DIAN. '
                                          'Set it up in the Journals configuration view in Odoo.'))

                    type_currencies_env = self.env['l10n_co_edi_jorels.type_currencies']
                    company_currency_search = type_currencies_env.search([('code', '=', company_currency_code)])
                    invoice_currency_search = type_currencies_env.search([('code', '=', invoice_currency_code)])

                    # The if is to make sure the name in currency_id,
                    # have a match in the code in type_currencies of the DIAN
                    if company_currency_search and invoice_currency_search:
                        rate_date = rec.date or rec.invoice_date or fields.Date.context_today(self)
                        rate = rec.currency_id.with_context(dict(rec._context or {}, date=rec.invoice_date)).rate

                        json_request['currency_code'] = company_currency_search.id
                        json_request['exchange_rate'] = {
                            'code': invoice_currency_search.id,
                            'rate': rate,
                            'date': str(rate_date)
                        }
                    else:
                        raise UserError(_("A currency type in Odoo does not correspond to any DIAN currency type"))

                if self.is_universal_discount():
                    if rec.currency_id and rec.company_id and rec.currency_id != rec.company_id.currency_id:
                        raise UserError(
                            _("The universal discount module doesn't seem to be compatible with multi-currencies."))

                    if rec.ks_amount_discount:
                        allowance_charges = []
                        allowance_charge = {
                            'indicator': False,
                            'discount_code': 2,
                            'base_value': abs(rec.amount_untaxed_signed),
                            'value': rec.ks_amount_discount,
                            'reason': 'Descuento general'
                        }
                        allowance_charges.append(allowance_charge)
                        json_request['allowance_charges'] = allowance_charges

                # json_request y billing_reference
                billing_reference = False
                type_edi_document = rec.ei_type_document
                invoice_rec = None
                json_request['legal_monetary_totals'] = rec.get_ei_legal_monetary_totals()
                json_request['lines'] = rec.get_ei_lines()
                json_request['payment_forms'] = [rec.get_ei_payment_form()]
                if type_edi_document in ('invoice', 'doc_support'):
                    # Sales invoice
                    billing_reference = False
                elif type_edi_document in ('credit_note', 'note_support'):
                    # Credit note
                    invoice_env = self.env['account.move']
                    invoice_rec = invoice_env.search([('id', '=', rec.reversed_entry_id.id)])
                    billing_reference = True
                elif type_edi_document == 'debit_note':
                    # Debit note
                    if self.is_debit_note_module():
                        if not rec.ei_is_correction_without_reference:
                            invoice_env = self.env['account.move']
                            invoice_rec = invoice_env.search([('id', '=', rec.debit_origin_id.id)])
                        billing_reference = True
                    else:
                        raise UserError(_("The debit notes module has not been installed."))

                # Billing reference
                if billing_reference:
                    rec.compute_ei_correction_concept_id()
                    if rec.ei_correction_concept_id:
                        json_request["discrepancy"] = {
                            # "reference": None,
                            "correction_code": rec.ei_correction_concept_id.id,
                            "description": rec.ref if rec.ref else ''
                        }
                    else:
                        raise UserError(_("You need to select a correction code first"))

                    if not rec.ei_is_correction_without_reference:
                        if invoice_rec and invoice_rec.ei_uuid:
                            json_request["reference"] = {
                                "number": invoice_rec.number_formatted,
                                "uuid": invoice_rec.ei_uuid,
                                "issue_date": fields.Date.to_string(invoice_rec.ei_issue_date)
                            }
                        else:
                            raise UserError(_("The reference invoice has not yet been validated before the DIAN"))
                    elif type_edi_document == 'note_support':
                        raise UserError(
                            _("The credit note for document support cannot be a correction without reference"))

                if rec.ref or rec.narration:
                    notes = []
                    if rec.ref:
                        notes.append({'text': rec.ref})
                    if rec.narration:
                        narration = re.sub(r'<.*?>', '', rec.narration)
                        if narration:
                            notes.append({'text': narration})
                    json_request['notes'] = notes
            else:
                raise UserError(_("This type of document does not need to be sent to DIAN"))

            return json_request

    def validate_dian_generic(self, is_test):
        for rec in self:
            try:
                if not rec.company_id.ei_enable:
                    continue

                # raise UserError(json.dumps(rec.get_json_request(), indent=2, sort_keys=False))
                _logger.debug("DIAN Validation Request: %s",
                              json.dumps(rec.get_json_request(), indent=2, sort_keys=False))

                if rec.state == 'draft':
                    raise UserError(_("The invoice must first be validated in Odoo, before being sent to the DIAN."))

                type_edi_document = rec.ei_type_document
                if rec.is_pending_to_send_to_dian():
                    requests_data = rec.get_json_request()

                    if rec.company_id.api_key:
                        token = rec.company_id.api_key
                    else:
                        raise UserError(_("You must configure a token"))

                    api_url = self.env['ir.config_parameter'].sudo().get_param('jorels.edipo.api_url',
                                                                               'https://edipo.jorels.com')
                    params = {'token': token}
                    header = {
                        "accept": "application/json",
                        "Content-Type": "application/json"
                    }

                    if rec.is_out_country:
                        params['export'] = True

                    api_url = api_url + "/" + type_edi_document

                    if is_test or not rec.ei_is_not_test:
                        if type_edi_document in ('doc_support', 'note_support'):
                            raise UserError(
                                _("The support document does not support test submissions, only production."))
                        if rec.company_id.test_set_id:
                            test_set_id = rec.company_id.test_set_id
                            params['test_set_id'] = test_set_id
                        else:
                            raise UserError(_("You have not configured a 'TestSetId'."))

                    _logger.debug('API URL: %s', api_url)

                    num_attemps = int(self.env['ir.config_parameter'].sudo().get_param('jorels.edipo.num_attemps', '2'))
                    if is_test or not rec.ei_is_not_test:
                        num_attemps = 1

                    for i in range(num_attemps):
                        try:
                            response = requests.post(api_url,
                                                     json.dumps(requests_data),
                                                     headers=header,
                                                     params=params).json()
                        except Exception as e:
                            _logger.warning("Invalid response: %s", e)

                        _logger.debug('API Response: %s', response)

                        if 'is_valid' in response and response['is_valid']:
                            break

                    if 'detail' in response:
                        raise UserError(response['detail'])
                    if 'message' in response:
                        if response['message'] == 'Unauthenticated.' or response['message'] == '':
                            raise UserError(_("Authentication error with the API"))
                        else:
                            if 'errors' in response:
                                raise UserError(response['message'] + '/ errors: ' + str(response['errors']))
                            else:
                                raise UserError(response['message'])
                    elif 'is_valid' in response:
                        rec.write_response(response, json.dumps(requests_data, indent=2, sort_keys=False))
                        if response['is_valid']:
                            # self.env.user.notify_success(message=_("The validation at DIAN has been successful."))
                            _logger.debug("The validation at DIAN has been successful.")
                        elif 'uuid' in response:
                            if response['uuid'] != "":
                                if not rec.ei_is_not_test:
                                    # self.env.user.notify_success(message=_("Document sent to DIAN in habilitation."))
                                    _logger.debug("Document sent to DIAN in habilitation.")
                                else:
                                    temp_message = {rec.ei_status_message, rec.ei_errors_messages,
                                                    rec.ei_status_description, rec.ei_status_code}
                                    raise UserError(str(temp_message))
                            else:
                                raise UserError(_('A valid UUID was not obtained. Try again.'))
                        else:
                            raise UserError(_('The document could not be validated in DIAN.'))
                    else:
                        raise UserError(_("No logical response was obtained from the API."))
                else:
                    _logger.debug("This document does not need to be sent to the DIAN")
            except Exception as e:
                _logger.debug("Failed to process the request for document: %s: %s", (rec.name, e))
                if not rec.company_id.ei_always_validate:
                    raise UserError(_("Failed to process the request for document: %s: %s") % (rec.name, e))
                else:
                    rec.message_post(body=_("DIAN Electronic invoicing: "
                                            "Failed to process the request for document: %s: %s") % (rec.name, e))

            if not is_test and not rec.ei_attached_document_base64_bytes:
                rec.status_document_log()
                if not rec.ei_attached_document_base64_bytes:
                    _logger.error('Unable to obtain an attached document.')

            if not rec.is_edi_mail_sent and rec.company_id.enable_mass_send_print and rec.is_to_send_edi_email():
                try:
                    rec.mass_send_print()
                except Exception:
                    rec._send_edi_email()
                rec.write({'is_edi_mail_sent': True})

    def validate_dian(self):
        for rec in self:
            if rec.state != 'draft':
                rec.validate_dian_generic(False)

    def validate_dian_test(self):
        for rec in self:
            rec.validate_dian_generic(True)

    def skip_validate_dian(self):
        for rec in self:
            rec.write({'state': 'posted'})
            # self.env.user.notify_warning(message=_("The validation process has been skipped."))
            _logger.debug("The validation process has been skipped.")

    def skip_validate_dian_production(self):
        for rec in self:
            rec.skip_validate_dian()

    def is_debit_note_module(self):
        self.ensure_one()
        return True if hasattr(self, 'debit_origin_id') else False

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft)

        to_edi = self.filtered(lambda inv: inv.is_pending_to_send_to_dian())
        if to_edi:
            # Invoices in DIAN cannot be validated with zero total
            to_paid_invoices = to_edi.filtered(lambda inv: inv.currency_id.is_zero(inv.amount_total))
            if to_paid_invoices and not self.company_id.ei_allow_zero_total:
                raise UserError(
                    _('Please check your invoice again. Are you really billing something? To allow zero total invoices, enable the option in Electronic Invoicing settings.'))

            # Validate invoices
            to_electronic_invoices = to_edi.filtered(lambda inv: inv.state == 'posted'
                                                                 and not inv.company_id.enable_validate_state)
            if to_electronic_invoices:
                to_electronic_invoices.filtered(lambda inv: inv.write({'ei_is_not_test': inv.company_id.is_not_test}))

                # Production invoices
                to_production_invoices = to_electronic_invoices.filtered(lambda inv: inv.ei_is_not_test)
                if to_production_invoices:
                    to_production_invoices.validate_dian_generic(False)

                # Test invoices
                to_test_invoices = to_electronic_invoices.filtered(lambda inv: not inv.ei_is_not_test)
                if to_test_invoices:
                    to_test_invoices.validate_dian_generic(True)

        return res

    def status_document(self):
        for rec in self:
            if not rec.company_id.ei_enable:
                continue

            try:
                # This line ensures that the electronic fields of the invoice are updated in Odoo, before the request
                requests_data = rec.get_json_request()
                _logger.debug('Customer data: %s', requests_data)

                if rec.should_send_document_to_dian():
                    if rec.ei_zip_key or rec.ei_uuid:
                        requests_data = {}
                        _logger.debug('API Requests: %s', requests_data)

                        if rec.company_id.api_key:
                            token = rec.company_id.api_key
                        else:
                            raise UserError(_("You must configure a token"))

                        api_url = self.env['ir.config_parameter'].sudo().get_param('jorels.edipo.api_url',
                                                                                   'https://edipo.jorels.com')
                        params = {
                            'token': token,
                            'environment': 1 if rec.ei_is_not_test else 2
                        }
                        header = {"accept": "application/json", "Content-Type": "application/json"}

                        if rec.ei_zip_key:
                            api_url = api_url + "/zip/" + rec.ei_zip_key
                        else:
                            api_url = api_url + "/document/" + rec.ei_uuid

                        _logger.debug('API URL: %s', api_url)

                        response = requests.post(api_url,
                                                 json.dumps(requests_data),
                                                 headers=header,
                                                 params=params).json()
                        _logger.debug('API Response: %s', response)

                        if 'detail' in response:
                            raise UserError(response['detail'])
                        if 'message' in response:
                            if response['message'] == 'Unauthenticated.' or response['message'] == '':
                                raise UserError(_("Authentication error with the API"))
                            else:
                                if 'errors' in response:
                                    raise UserError(response['message'] + '/ errors: ' + str(response['errors']))
                                else:
                                    raise UserError(response['message'])
                        elif 'is_valid' in response:
                            rec.write_response(response, json.dumps(requests_data, indent=2, sort_keys=False))
                            if response['is_valid']:
                                # self.env.user.notify_info(message=_("Validation in DIAN has been successful."))
                                _logger.debug("Validation in DIAN has been successful.")
                            elif 'zip_key' in response or 'uuid' in response:
                                if response['zip_key'] is not None or response['uuid'] is not None:
                                    if not rec.ei_is_not_test:
                                        # self.env.user.notify_info(message=_("Document sent to DIAN in testing."))
                                        _logger.debug("Document sent to DIAN in testing.")
                                    else:
                                        temp_message = {rec.ei_status_message, rec.ei_errors_messages,
                                                        rec.ei_status_description, rec.ei_status_code}
                                        raise UserError(str(temp_message))
                                else:
                                    raise UserError(_('A valid Zip key or UUID was not obtained. Try again.'))
                            else:
                                raise UserError(_('The document could not be validated in DIAN.'))
                        else:
                            raise UserError(_("No logical response was obtained from the API"))
                    else:
                        raise UserError(_("A Zip key or UUID is required to check the status of the document."))
                else:
                    raise UserError(_("This type of document does not need to be sent to the DIAN"))
            except Exception as e:
                _logger.debug("Failed to process the request: %s", e)
                raise UserError(_("Failed to process the request: %s") % e)

    def status_document_log(self):
        for rec in self:
            if not rec.company_id.ei_enable:
                continue

            try:
                # This line ensures that the electronic fields of the invoice are updated in Odoo,
                # before request
                requests_data = rec.get_json_request(check_date=False)
                _logger.debug('Customer data: %s', requests_data)

                if rec.should_send_document_to_dian():
                    if rec.number_formatted:
                        requests_data = {}
                        _logger.debug('API Requests: %s', requests_data)

                        if rec.company_id.api_key:
                            token = rec.company_id.api_key
                        else:
                            raise UserError(_("You must configure a token"))

                        api_url = self.env['ir.config_parameter'].sudo().get_param('jorels.edipo.api_url',
                                                                                   'https://edipo.jorels.com')
                        params = {'token': token}
                        header = {"accept": "application/json", "Content-Type": "application/json"}

                        api_url = api_url + "/logs/" + rec.number_formatted

                        _logger.debug('API URL: %s', api_url)

                        response = requests.post(api_url,
                                                 json.dumps(requests_data),
                                                 headers=header,
                                                 params=params).json()
                        _logger.debug('API Response: %s', response)

                        if 'detail' in response:
                            raise UserError(response['detail'])
                        if 'message' in response:
                            if response['message'] == 'Unauthenticated.' or response['message'] == '':
                                # self.env.user.notify_warning(message=_("Authentication error with the API"))
                                _logger.debug(_("Authentication error with the API"))
                            else:
                                if 'errors' in response:
                                    # self.env.user.notify_warning(
                                    #     message=response['message'] + '/ errors: ' + str(response['errors']))
                                    _logger.debug(response['message'] + '/ errors: ' + str(response['errors']))
                                else:
                                    # self.env.user.notify_warning(message=response['message'])
                                    _logger.debug(response['message'])
                        elif response and ('is_valid' in response[0]):
                            success = False
                            for log in response:
                                if log['is_valid']:
                                    json_request = json.loads(json.dumps(log))
                                    rec.ei_is_valid = json_request['is_valid']
                                    if json_request['algorithm']:
                                        rec.ei_algorithm = json_request['algorithm']
                                    if json_request['uuid']:
                                        rec.ei_uuid = json_request['uuid']
                                    if json_request['issue_date']:
                                        rec.ei_issue_date = json_request['issue_date']
                                        rec.ei_issue_datetime = json_request['issue_date']
                                    if json_request['zip_key']:
                                        rec.ei_zip_key = json_request['zip_key']
                                    if json_request['xml_name']:
                                        rec.ei_xml_name = json_request['xml_name']
                                    if json_request['zip_name']:
                                        rec.ei_zip_name = json_request['zip_name']
                                    if json_request['xml_base64_bytes']:
                                        rec.ei_xml_base64_bytes = json_request['xml_base64_bytes']
                                    if json_request['qr_data']:
                                        rec.ei_qr_data = json_request['qr_data']
                                    if json_request['application_response_base64_bytes']:
                                        rec.ei_application_response_base64_bytes = json_request[
                                            'application_response_base64_bytes']
                                    if json_request['attached_document_base64_bytes']:
                                        rec.ei_attached_document_base64_bytes = json_request[
                                            'attached_document_base64_bytes']
                                    if json_request['pdf_base64_bytes']:
                                        rec.ei_pdf_base64_bytes = json_request['pdf_base64_bytes']
                                    if json_request['zip_base64_bytes']:
                                        rec.ei_zip_base64_bytes = json_request['zip_base64_bytes']
                                    if json_request['signature']:
                                        rec.ei_signature = json_request['signature']

                                        # QR code
                                        qr = qrcode.QRCode(
                                            version=1,
                                            error_correction=qrcode.constants.ERROR_CORRECT_M,
                                            box_size=2,
                                            border=2,
                                        )
                                        qr.add_data(rec.ei_qr_data)
                                        qr.make(fit=True)
                                        img = qr.make_image()
                                        temp = BytesIO()
                                        img.save(temp, format="PNG")
                                        qr_image = base64.b64encode(temp.getvalue())
                                        rec.ei_qr_image = qr_image

                                    success = True
                                    break
                            if success:
                                # self.env.user.notify_info(message=_("Validation in DIAN has been successful."))
                                _logger.debug("Validation in DIAN has been successful.")
                                rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                                        "Validation in DIAN has been successful."))
                            else:
                                # self.env.user.notify_warning(message=_("The document has not been validated."))
                                _logger.debug("The document has not been validated.")
                                rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                                        "The document has not been validated."))
                        else:
                            # self.env.user.notify_warning(message=_("The document could not be consulted."))
                            _logger.debug("The document could not be consulted.")
                            rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                                    "The document could not be consulted."))
                    else:
                        # self.env.user.notify_warning(
                        #     message=_("A number is required to verify the status of the document."))
                        _logger.debug("A number is required to verify the status of the document.")
                        rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                                "A number is required to verify the status of the document."))
                else:
                    # self.env.user.notify_warning(message=_("This type of document does not need to be sent to DIAN."))
                    _logger.debug("This type of document does not need to be sent to DIAN.")
                    rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                            "This type of document does not need to be sent to DIAN."))
            except Exception as e:
                # self.env.user.notify_warning(message=_("Failed to process the request"))
                _logger.debug("Failed to process the request: %s", e)
                rec.message_post(body=_("Log DIAN Electronic invoicing: "
                                        "Failed to process the request for document: %s: %s") % (rec.name, e))

    @api.depends('ei_attached_document_base64_bytes')
    def _is_attached_document_matched(self):
        for rec in self:
            if not rec.company_id.ei_enable:
                continue

            if rec.ei_attached_document_base64_bytes:
                with BytesIO(base64.b64decode(rec.ei_attached_document_base64_bytes)) as file:
                    search_ok = False
                    for line in file:
                        if rec.number_formatted and isinstance(rec.number_formatted, str):
                            search_string = '<cbc:ParentDocumentID>' + rec.number_formatted + '</cbc:ParentDocumentID>'
                            if search_string in str(line):
                                search_ok = True
                                break
                    rec.is_attached_document_matched = search_ok
            else:
                rec.is_attached_document_matched = False

    def create_radian_default_events(self):
        search_env = self.env['l10n_co_edi_jorels.radian']

        for rec in self:
            if rec.move_type in ('out_invoice', 'out_refund') and rec.payment_form_id.id == 2:
                event_type = 'customer'

                # Tacit acceptance
                search_rec = search_env.search([('move_id', '=', rec.id), ('event_id', '=', 7)])
                if not search_rec:
                    search_env.create({
                        'move_id': rec.id,
                        'event_id': 7,
                        'type': event_type,
                    })

            if rec.move_type in ('in_invoice', 'in_refund') and rec.payment_form_id.id == 2:
                event_type = 'supplier'

                # Acknowledgment of receipt of the Electronic Bill of Sale
                search_rec = search_env.search([('move_id', '=', rec.id), ('event_id', '=', 3)])
                if not search_rec:
                    search_env.create({
                        'move_id': rec.id,
                        'event_id': 3,
                        'type': event_type,
                    })

                # Receipt of the good and/or provision of the service
                search_rec = search_env.search([('move_id', '=', rec.id), ('event_id', '=', 5)])
                if not search_rec:
                    search_env.create({
                        'move_id': rec.id,
                        'event_id': 5,
                        'type': event_type,
                    })

                # Express acceptance
                search_rec = search_env.search([('move_id', '=', rec.id), ('event_id', '=', 6)])
                if not search_rec:
                    search_env.create({
                        'move_id': rec.id,
                        'event_id': 6,
                        'type': event_type,
                    })

    def get_uuid_from_nimbus(self):
        for rec in self:
            if not rec.company_id.ei_enable:
                continue

            try:
                if rec.should_send_document_to_dian() and rec.move_type in ('in_invoice', 'in_refund'):
                    if rec.move_type == 'in_invoice':
                        if ((('debit_origin_id' in rec) and rec.debit_origin_id)
                                or rec.ei_is_correction_without_reference):
                            # Supplier Debit Note
                            nimbus_type_document_code = '192'
                        elif rec.is_out_country:
                            # Supplier Export Invoice
                            nimbus_type_document_code = '102'
                        else:
                            # Supplier Invoice
                            nimbus_type_document_code = '101'
                    elif rec.move_type == 'in_refund':
                        # Supplier Credit Note
                        nimbus_type_document_code = '191'
                    else:
                        _logger.debug(_("This type of document does not is a Nimbus compatible document"))
                        continue

                    if rec.number_formatted:
                        if rec.company_id.nimbus_api_key:
                            token = rec.company_id.nimbus_api_key
                        else:
                            raise UserError(_("You must configure a Nimbus token"))

                        api_url = self.env['ir.config_parameter'].sudo().get_param('jorels.nimbus.api_url',
                                                                                   'https://nimbus.jorels.com')

                        header = {
                            "accept": "application/json",
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + token
                        }

                        api_url = "{}/edi/{}/{}/{}".format(
                            api_url,
                            rec.partner_id.edi_sanitize_vat,
                            nimbus_type_document_code,
                            rec.ref
                        )

                        _logger.debug('API URL: %s', api_url)

                        response = requests.get(api_url, headers=header).json()
                        _logger.debug('Nimbus API Response: %s', response)

                        if 'detail' in response:
                            raise UserError(response['detail'])
                        elif 'is_valid' in response:
                            if response['is_valid']:
                                rec.ei_is_valid = response['is_valid']
                                rec.ei_uuid = response['uuid']
                                # rec.ei_issue_date = response['date_issue']
                                # rec.ei_issue_datetime = response['date_issue']
                                # TODO: Quedan campos pendientes de agregar
                            else:
                                rec.message_post(body=_("There is no associated document in Nimbus"))
                                _logger.debug(_('There is no associated document in Nimbus'))
                        else:
                            rec.message_post(body=_("No logical response was obtained from the Nimbus API"))
                            _logger.debug(_("No logical response was obtained from the Nimbus API"))
                    else:
                        rec.message_post(body=_("A Edi number is required to check the document in Nimbus"))
                        _logger.debug(_("A Edi number is required to check the document in Nimbus"))
                else:
                    rec.message_post(body=_("This type of document does not is a Nimbus compatible document"))
                    _logger.debug(_("This type of document does not is a Nimbus compatible document"))
            except Exception as e:
                rec.message_post(body=_("Failed to process the Nimbus request: %s: %s") % (rec.name, e))
                _logger.debug("Failed to process the Nimbus request: %s", e)

    def _process_attachments_for_template_post(self, mail_template):
        """ Add Edi attachments to templates. """
        result = super()._process_attachments_for_template_post(mail_template)

        attachments = []
        edi_attachments = {}
        for move in self.filtered(lambda m: m.is_to_send_edi_email()):
            move_result = result.setdefault(move.id, {})

            if not move.company_id.ei_enable or not move.is_to_send_edi_email():
                continue

            move._compute_attached_zip_file()
            attached_document_name = move._compute_attached_document_name()
            zip_name = f"{attached_document_name}.zip"
            attachments += [(zip_name, move.ei_attached_zip_base64_bytes)]

            edi_attachments = {'attachments': attachments}
            move_result.setdefault('attachment_ids', []).extend(edi_attachments.get('attachment_ids', []))
            move_result.setdefault('attachments', []).extend(edi_attachments.get('attachments', []))
        return result

    def _compute_attached_document_name(self):
        self.ensure_one()
        if self.ei_zip_name:
            attached_document_name = 'ad' + self.ei_zip_name[1:-4]
        else:
            attached_document_name = self.ei_uuid

        return attached_document_name

    def _compute_attached_zip_file(self):
        for move in self:
            if not move.ei_attached_document_base64_bytes:
                continue

            attached_document_name = move._compute_attached_document_name()

            # Create temporary directory for all files
            temp_dir = Path(tempfile.gettempdir())

            # Define file paths
            pdf_name = attached_document_name + '.pdf'
            pdf_path = temp_dir / pdf_name

            xml_name = attached_document_name + '.xml'
            xml_path = temp_dir / xml_name

            zip_name = attached_document_name + '.zip'
            zip_path = temp_dir / zip_name

            # Create main zip file
            with zipfile.ZipFile(zip_path, 'w') as zip_archive:
                # Generate default Odoo PDF report
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    'account.account_invoices',
                    move.ids
                )

                # Add PDF to zip
                with open(pdf_path, 'wb') as pdf_handle:
                    pdf_handle.write(pdf_content)
                zip_archive.write(pdf_path, arcname=pdf_name)

                # Add XML to zip
                with open(xml_path, 'wb') as xml_handle:
                    xml_handle.write(base64.decodebytes(move.ei_attached_document_base64_bytes))
                zip_archive.write(xml_path, arcname=xml_name)

                # If there are additional documents, create a secondary zip
                if move.ei_additional_documents:
                    additional_zip_name = f"{attached_document_name}_additional_documents.zip"
                    additional_zip_path = temp_dir / additional_zip_name

                    with zipfile.ZipFile(additional_zip_path, 'w') as additional_zip:
                        for attachment in move.ei_additional_documents:
                            attachment_path = temp_dir / attachment.name
                            with open(attachment_path, 'wb') as attachment_handle:
                                attachment_handle.write(base64.b64decode(attachment.datas))
                            additional_zip.write(attachment_path, arcname=attachment.name)
                            # Clean up temporary attachment file
                            attachment_path.unlink()

                    # Add secondary zip to main zip
                    zip_archive.write(additional_zip_path, arcname=additional_zip_name)
                    # Clean up secondary zip file
                    additional_zip_path.unlink()

            # Read and encode the final zip file
            with open(zip_path, 'rb') as f:
                attached_zip = f.read()
                ei_attached_zip_base64_bytes = base64.encodebytes(attached_zip)
                move.write({
                    'ei_attached_zip_base64_bytes': ei_attached_zip_base64_bytes
                })

            # Clean up temporary files
            pdf_path.unlink()
            xml_path.unlink()
            zip_path.unlink()

    def action_send_and_print(self):
        for rec in self:
            if not rec.company_id.ei_enable or not rec.is_to_send_edi_email():
                continue

            rec._compute_attached_zip_file()

        return super().action_send_and_print()

    @api.depends('currency_id', 'company_currency_id')
    def _compute_is_multicurrency(self):
        for invoice in self:
            invoice.is_multicurrency = invoice.currency_id != invoice.company_currency_id
