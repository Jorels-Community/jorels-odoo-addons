# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2022)
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
import hashlib
import hmac
import json
import logging
import time

import requests
from odoo import api, fields, http, SUPERUSER_ID, _
from odoo.http import request

_logger = logging.getLogger(__name__)

MAX_TIMESTAMP_DIFF = 300  # 5 minutes

# Mapping from DIAN document type code to (account.invoice.type, ei_type_document)
DOCUMENT_TYPE_MAP = {
    '01': ('in_invoice', 'invoice'),
    '02': ('in_invoice', 'invoice'),
    '91': ('in_refund', 'credit_note'),
    '92': ('in_invoice', 'debit_note'),
    '20': ('in_invoice', 'invoice'),
    '94': ('in_refund', 'credit_note'),
    '60': ('in_invoice', 'invoice'),
    '35': ('in_invoice', 'invoice'),
    '45': ('in_invoice', 'invoice'),
    '50': ('in_invoice', 'invoice'),
    '32': ('in_invoice', 'invoice'),
    '40': ('in_invoice', 'invoice'),
    '55': ('in_invoice', 'invoice'),
    '27': ('in_invoice', 'invoice'),
    '25': ('in_invoice', 'invoice'),
}


def _get_nimbus_secret(company):
    """
    Get the NIMBUS webhook secret for a specific company.

    The webhook secret is configured per company and is required to validate
    the HMAC-SHA256 signature of incoming webhooks.

    Args:
        company (res.company): Company record.

    Returns:
        str: Webhook secret or empty string if not configured.
    """
    return company.nimbus_webhook_secret or '' if company else ''


def _get_nimbus_api_url(env):
    """
    Get the NIMBUS API URL from system parameters.

    Args:
        env: Odoo environment.

    Returns:
        str: API URL.
    """
    return env['ir.config_parameter'].sudo().get_param(
        'jorels.nimbus.api_url', 'https://nimbus.jorels.com/api'
    )


def _verify_signature(secret, payload_bytes, signature_header):
    """
    Verify HMAC-SHA256 signature from NIMBUS webhook.

    Args:
        secret (str): Webhook secret.
        payload_bytes (bytes): Raw request body.
        signature_header (str): Value of X-Nimbus-Signature header.

    Returns:
        bool: True if signature is valid.
    """
    if not signature_header:
        return False
    if signature_header.startswith('sha256='):
        expected_sig = signature_header[7:]
    else:
        expected_sig = signature_header
    computed_sig = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed_sig, expected_sig)


def _verify_timestamp(timestamp_header):
    """
    Verify that the webhook timestamp is within acceptable range.

    Args:
        timestamp_header (str): Unix timestamp string.

    Returns:
        bool: True if timestamp is valid.
    """
    try:
        webhook_ts = int(timestamp_header)
        now = int(time.time())
        diff = abs(now - webhook_ts)
        return diff <= MAX_TIMESTAMP_DIFF
    except (ValueError, TypeError):
        return False


def _download_nimbus_attachments(edi_id, company):
    """
    Download attachments from NIMBUS API.

    Args:
        edi_id (int): EDI document ID.
        company (res.company): Company record with API credentials.

    Returns:
        list: List of attachment dicts with file_name, type, and document base64.
    """
    env = request.env
    api_url = _get_nimbus_api_url(env)
    token = company.nimbus_api_key

    if not token:
        _logger.warning(
            "Cannot download NIMBUS attachments: nimbus_api_key not configured"
        )
        return []

    url = "{}/attachments/{}".format(api_url, edi_id)
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        _logger.info(
            "NIMBUS attachments response: status=%s url=%s",
            response.status_code, url,
        )
        response.raise_for_status()
        attachments = response.json()
        _logger.info(
            "Downloaded %d attachments from NIMBUS for edi_id=%s",
            len(attachments), edi_id,
        )
        return attachments
    except Exception as e:
        _logger.warning(
            "Failed to download NIMBUS attachments for edi_id=%s: %s",
            edi_id, e,
        )
        return []


def _find_or_create_partner(env, data):
    """
    Find or create a supplier partner based on webhook data.

    Args:
        env: Odoo environment.
        data (dict): Webhook payload data.

    Returns:
        res.partner: Partner record.
    """
    vat = data.get('vat') or data.get('supplier_identification', '')
    if not vat:
        _logger.warning("No VAT provided in webhook, cannot find/create partner")
        return env['res.partner']

    partner = env['res.partner'].search([
        ('edi_sanitize_vat', '=', vat),
        ('supplier', '=', True),
    ], limit=1)

    if partner:
        _logger.info("Found existing partner for VAT %s: %s", vat, partner.name)
        # Update missing fields
        vals = {}
        if data.get('sender_email') and not partner.email:
            vals['email'] = data['sender_email']
        if data.get('trade_name') and not partner.name:
            vals['name'] = data['trade_name']
        elif data.get('name') and not partner.name:
            vals['name'] = data['name']
        if vals:
            partner.write(vals)
        return partner

    # Create new partner as natural person (cedula de ciudadania)
    name = data.get('trade_name') or data.get('name') or 'Unknown'
    partner_vals = {
        'name': name,
        'vat': vat,
        'type_document_identification_id': env.ref(
            'l10n_co_edi_jorels.type_document_identification_3', raise_if_not_found=False
        ).id if env.ref('l10n_co_edi_jorels.type_document_identification_3', raise_if_not_found=False) else False,
        'email': data.get('sender_email', ''),
        'supplier': True,
        'is_company': False,
        'customer': False,
    }

    partner = env['res.partner'].create(partner_vals)
    _logger.info("Created new partner for VAT %s: %s", vat, partner.name)
    return partner


def _map_document_type(document_type_code):
    """
    Map DIAN document type code to Odoo invoice type and EDI document type.

    Args:
        document_type_code (str): DIAN document type code.

    Returns:
        tuple: (invoice_type, edi_type_document) or (None, None) if unsupported.
    """
    return DOCUMENT_TYPE_MAP.get(document_type_code, (None, None))


def _handle_invoice_received(env, company, data, attachments, delivery_id):
    """
    Process an incoming invoice webhook from NIMBUS for a specific company.

    Args:
        env: Odoo environment.
        company (res.company): Company that receives the webhook.
        data (dict): Webhook payload data.
        attachments (list): List of downloaded attachments.
        delivery_id (str): Webhook delivery ID.

    Returns:
        dict: Response dict with status and message.
    """
    document_type_code = data.get('document_type_code', '')
    invoice_type, edi_type = _map_document_type(document_type_code)

    if invoice_type is None:
        _logger.warning(
            "Unsupported document type code received: %s. Skipping invoice creation.",
            document_type_code,
        )
        return {
            'status': 'error',
            'message': 'Unsupported document type code: {}'.format(document_type_code),
        }

    # Find or create partner
    partner = _find_or_create_partner(env, data)
    if not partner:
        return {
            'status': 'error',
            'message': 'Could not find or create partner for VAT: {}'.format(
                data.get('vat')
            ),
        }

    # Find document type
    type_document = env['l10n_co_edi_jorels.type_documents'].search([
        ('code', '=', document_type_code),
    ], limit=1)

    # Extract XML and PDF from attachments
    xml_base64 = None
    pdf_base64 = None
    for att in attachments:
        if att.get('type') == 'xml' and att.get('document'):
            xml_base64 = att['document']
        elif att.get('type') == 'pdf' and att.get('document'):
            pdf_base64 = att['document']

    # Prepare invoice values
    invoice_vals = {
        'type': invoice_type,
        'company_id': company.id,
        'partner_id': partner.id,
        'reference': data.get('number', ''),
        'date_invoice': data.get('document_date'),
        'date_due': data.get('due_date'),
        'origin': data.get('sender_email', ''),
        'state': 'draft',
        'ei_is_valid': True,
        'ei_uuid': data.get('uuid', ''),
        'ei_type_document_id': type_document.id if type_document else False,
        'ei_type_document': edi_type,
        'ei_issue_date': data.get('document_date'),
    }

    if xml_base64:
        invoice_vals['ei_attached_document_base64_bytes'] = xml_base64
    if pdf_base64:
        invoice_vals['ei_pdf_base64_bytes'] = pdf_base64

    invoice = env['account.invoice'].create(invoice_vals)
    _logger.info(
        "Created invoice %s (type=%s, company=%s) from NIMBUS webhook for partner %s",
        invoice.number or invoice.reference, invoice_type, company.name, partner.name,
    )

    # Update log
    log = env['l10n_co_edi_jorels.nimbus_webhook_log'].search([
        ('company_id', '=', company.id),
        ('delivery_id', '=', delivery_id),
    ], limit=1)
    if log:
        log.write({
            'state': 'done',
            'invoice_id': invoice.id,
        })

    return {
        'status': 'ok',
        'message': 'Invoice created successfully',
        'invoice_id': invoice.id,
    }


def _handle_event_received(env, company, data, attachments, delivery_id):
    """
    Process an incoming event webhook from NIMBUS for a specific company.

    Args:
        env: Odoo environment.
        company (res.company): Company that receives the webhook.
        data (dict): Webhook payload data.
        attachments (list): List of downloaded attachments.
        delivery_id (str): Webhook delivery ID.

    Returns:
        dict: Response dict with status and message.
    """
    # Search for the referenced invoice scoped to the company.
    # NIMBUS events include number_reference with the original invoice number.
    uuid = data.get('uuid', '')
    number = data.get('number', '')
    number_reference = data.get('number_reference', '')
    vat = data.get('vat') or data.get('supplier_identification', '')

    invoice = env['account.invoice']

    # 1) Try by UUID (for backward compatibility / direct invoice events)
    if uuid:
        invoice = env['account.invoice'].search([
            ('company_id', '=', company.id),
            ('ei_uuid', '=', uuid),
        ], limit=1)

    # 2) Try by number_reference + VAT (RADIAN events reference the invoice)
    if not invoice and number_reference and vat:
        partner = env['res.partner'].search([
            ('edi_sanitize_vat', '=', vat),
        ], limit=1)
        if partner:
            invoice = env['account.invoice'].search([
                ('company_id', '=', company.id),
                ('reference', '=', number_reference),
                ('partner_id', '=', partner.id),
            ], limit=1)

    # 3) Fallback: event number + VAT (legacy behaviour)
    if not invoice and number and vat:
        partner = env['res.partner'].search([
            ('edi_sanitize_vat', '=', vat),
        ], limit=1)
        if partner:
            invoice = env['account.invoice'].search([
                ('company_id', '=', company.id),
                ('reference', '=', number),
                ('partner_id', '=', partner.id),
            ], limit=1)

    if not invoice:
        _logger.warning(
            "Could not find invoice for event webhook: uuid=%s number_reference=%s number=%s vat=%s",
            uuid, number_reference, number, vat,
        )
        log = env['l10n_co_edi_jorels.nimbus_webhook_log'].search([
            ('company_id', '=', company.id),
            ('delivery_id', '=', delivery_id),
        ], limit=1)
        if log:
            log.write({
                'state': 'error',
                'error_message': 'Invoice not found for UUID: {} / Number reference: {} / Number: {}'.format(
                    uuid, number_reference, number
                ),
            })
        return {
            'status': 'error',
            'message': 'Invoice not found for event',
        }

    # Determine event type (customer vs supplier)
    if invoice.type in ('out_invoice', 'out_refund'):
        event_type = 'customer'
    else:
        event_type = 'supplier'

    # Find event by code
    event_code = data.get('document_type_code', '')
    event_record = env['l10n_co_edi_jorels.events'].search([
        ('code', '=', event_code),
    ], limit=1)

    if not event_record:
        _logger.warning("Event code not found: %s", event_code)
        return {
            'status': 'error',
            'message': 'Event code not found: {}'.format(event_code),
        }

    # Extract XML and PDF from attachments
    xml_base64 = None
    pdf_base64 = None
    for att in attachments:
        if att.get('type') == 'xml' and att.get('document') and not xml_base64:
            xml_base64 = att['document']
        elif att.get('type') == 'pdf' and att.get('document') and not pdf_base64:
            pdf_base64 = att['document']

    # Create RADIAN event
    radian_vals = {
        'company_id': company.id,
        'invoice_id': invoice.id,
        'type': event_type,
        'event_id': event_record.id,
        'state': 'draft',
    }
    if xml_base64:
        radian_vals['edi_xml_base64'] = xml_base64
    if pdf_base64:
        radian_vals['edi_pdf_base64'] = pdf_base64

    radian = env['l10n_co_edi_jorels.radian'].create(radian_vals)

    # Generate sequence number (simulate action_post behavior for numbering)
    name_sequence = "radian_{}_{}".format(event_record.code, event_type)
    seq = env['ir.sequence'].search([('code', '=', name_sequence)], limit=1)
    if seq:
        next_name = seq.with_context(
            force_company=company.id
        ).next_by_code(name_sequence)
        if next_name:
            prefix, suffix = seq._get_prefix_suffix()
            number_str = ''.join([i for i in next_name[len(prefix):] if i.isdigit()])
            radian.write({
                'name': next_name,
                'prefix': prefix,
                'number': int(number_str) if number_str else 0,
            })

    # Post message on invoice chatter
    invoice.message_post(
        body=_("NIMBUS event received: {} ({})").format(
            event_record.name, event_code
        ),
        subject=_("Event {} - {}").format(event_code, invoice.reference or invoice.number),
    )

    _logger.info(
        "Created RADIAN event %s (type=%s, code=%s) for invoice %s",
        radian.name, event_type, event_code, invoice.reference or invoice.number,
    )

    # Update log
    log = env['l10n_co_edi_jorels.nimbus_webhook_log'].search([
        ('company_id', '=', company.id),
        ('delivery_id', '=', delivery_id),
    ], limit=1)
    if log:
        log.write({
            'state': 'done',
            'event_id': radian.id,
        })

    return {
        'status': 'ok',
        'message': 'Event created successfully',
        'event_id': radian.id,
    }


class Webhooks(http.Controller):

    @http.route(
        '/l10n_co_edi_jorels/webhook/nimbus/<int:company_id>',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def webhook_nimbus(self, company_id, **kwargs):
        """
        Receive webhooks from NIMBUS for incoming EDI documents and events.

        Validates HMAC-SHA256 signature, timestamp, processes invoices and events.
        The company_id in the URL identifies which Odoo company should receive
        and process the webhook.
        """
        env = api.Environment(request.env.cr, SUPERUSER_ID, request.env.context)
        payload_bytes = request.httprequest.data

        # Validate company
        company = env['res.company'].browse(company_id)
        if not company.exists():
            _logger.warning("NIMBUS webhook rejected: company %s does not exist", company_id)
            return {
                'status': 'error',
                'message': 'Company not found: {}'.format(company_id),
            }

        # Read headers
        signature = request.httprequest.headers.get('X-Nimbus-Signature', '')
        timestamp = request.httprequest.headers.get('X-Nimbus-Timestamp', '')
        delivery_id = request.httprequest.headers.get('X-Nimbus-Delivery-Id', '')
        idempotency_key = request.httprequest.headers.get('Idempotency-Key', '')
        event_type = request.httprequest.headers.get('X-Nimbus-Event', '')

        _logger.info(
            "NIMBUS webhook received: company_id=%s delivery_id=%s event=%s idempotency_key=%s",
            company_id, delivery_id, event_type, idempotency_key,
        )

        # Get secret for the specific company
        secret = _get_nimbus_secret(company)
        if not secret:
            _logger.error(
                "NIMBUS webhook rejected: secret not configured. "
                "Please set company.nimbus_webhook_secret"
            )
            return {
                'status': 'error',
                'message': 'Webhook secret not configured',
            }

        # Verify signature
        if not _verify_signature(secret, payload_bytes, signature):
            _logger.warning(
                "NIMBUS webhook rejected: invalid signature. "
                "delivery_id=%s signature=%s",
                delivery_id, signature,
            )
            return {
                'status': 'error',
                'message': 'Invalid signature',
            }

        # Verify timestamp
        if not _verify_timestamp(timestamp):
            _logger.warning(
                "NIMBUS webhook rejected: timestamp out of range. "
                "delivery_id=%s timestamp=%s",
                delivery_id, timestamp,
            )
            return {
                'status': 'error',
                'message': 'Timestamp out of range',
            }

        # Parse payload
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as e:
            _logger.warning(
                "NIMBUS webhook rejected: invalid JSON. delivery_id=%s error=%s",
                delivery_id, e,
            )
            return {
                'status': 'error',
                'message': 'Invalid JSON payload',
            }

        data = payload.get('data', {})
        edi_id = data.get('edi_id')

        # Idempotency check (scoped by company)
        existing_log = env['l10n_co_edi_jorels.nimbus_webhook_log'].search([
            ('company_id', '=', company.id),
            ('delivery_id', '=', delivery_id),
        ], limit=1)
        if existing_log and existing_log.state == 'done':
            _logger.info(
                "NIMBUS webhook idempotent: company=%s delivery_id=%s already processed",
                company.id, delivery_id,
            )
            return {
                'status': 'ok',
                'message': 'Webhook already processed',
                'delivery_id': delivery_id,
            }

        # Create or update log entry
        log_vals = {
            'company_id': company.id,
            'delivery_id': delivery_id,
            'event_type': event_type,
            'edi_id': edi_id,
            'timestamp': fields.Datetime.now(),
            'payload': json.dumps(payload, indent=2, ensure_ascii=False),
            'state': 'pending',
        }
        if existing_log:
            existing_log.write(log_vals)
        else:
            env['l10n_co_edi_jorels.nimbus_webhook_log'].create(log_vals)

        # Download attachments from NIMBUS
        _logger.info(
            "About to download attachments: edi_id=%s company=%s api_key=%s",
            edi_id, company.id, bool(company.nimbus_api_key),
        )
        attachments = _download_nimbus_attachments(edi_id, company)

        # Process based on event type
        try:
            if event_type == 'edi.invoice.received':
                result = _handle_invoice_received(env, company, data, attachments, delivery_id)
            elif event_type == 'edi.event.received':
                result = _handle_event_received(env, company, data, attachments, delivery_id)
            else:
                _logger.warning("Unknown event type: %s", event_type)
                result = {
                    'status': 'error',
                    'message': 'Unknown event type: {}'.format(event_type),
                }
        except Exception as e:
            _logger.error(
                "Error processing NIMBUS webhook: company=%s delivery_id=%s error=%s",
                company.id, delivery_id, e, exc_info=True,
            )
            log = env['l10n_co_edi_jorels.nimbus_webhook_log'].search([
                ('company_id', '=', company.id),
                ('delivery_id', '=', delivery_id),
            ], limit=1)
            if log:
                log.write({
                    'state': 'error',
                    'error_message': str(e),
                })
            result = {
                'status': 'error',
                'message': str(e),
            }

        # Return ok even for business errors so NIMBUS doesn't retry
        if result.get('status') == 'error':
            return result

        return {
            'status': 'ok',
            'message': result.get('message', 'Webhook processed successfully'),
            'delivery_id': delivery_id,
            'edi_id': edi_id,
        }
