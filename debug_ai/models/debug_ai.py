# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2024)
#
# This file is part of debug_ai.
#
# debug_ai is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# debug_ai is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with debug_ai.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import json
import logging

import requests
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    claude_prompt = fields.Text(string="Debug AI Prompt",
                                help="Enter instructions for Debug AI to generate a new inherited view")
    claude_edit_prompt = fields.Text(string="Debug AI Edit Prompt",
                                     help="Enter instructions for Debug AI to modify this view")

    def generate_inherited_view_with_claude(self):
        self.ensure_one()
        if not self.claude_prompt:
            raise UserError(_("Please enter a prompt for Debug AI"))

        studio = self.env['debug.ai'].create({
            'name': f"Generated view for {self.name}",
            'model_id': self.env['ir.model']._get(self.model).id,
            'view_id': self.id,
            'prompt': self.claude_prompt,
        })

        studio.process_prompt()

        # Clear the prompt after processing
        self.claude_prompt = False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'res_id': int(studio.result.split(':')[-1].strip()),
            'view_mode': 'form',
            'target': 'current',
        }

    def edit_view_with_claude(self):
        self.ensure_one()
        if not self.claude_edit_prompt:
            raise UserError(_("Please enter a prompt for editing the view"))

        studio = self.env['debug.ai'].create({
            'name': f"Edit view {self.name}",
            'model_id': self.env['ir.model']._get(self.model).id,
            'view_id': self.id,
            'prompt': self.claude_edit_prompt,
            'is_edit_mode': True,
        })

        studio.process_prompt()

        # Clear the prompt after processing
        self.claude_edit_prompt = False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ClaudeStudio(models.Model):
    _name = 'debug.ai'
    _description = 'Debug AI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade', tracking=True)
    view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete='cascade', tracking=True)
    prompt = fields.Text(string='Instructions', required=True, tracking=True)
    result = fields.Text(string='Result', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('applied', 'Applied'),
        ('error', 'Error')
    ], string='State', default='draft', required=True, tracking=True)
    is_edit_mode = fields.Boolean(string='Edit Mode', default=False, tracking=True)

    prompt_processing_date = fields.Datetime(
        string='AI Processing Date',
        readonly=True,
        help='Date and time when the prompt was processed by the AI'
    )
    view_update_date = fields.Datetime(
        string='View Update Date',
        readonly=True,
        help='Date and time when the view was updated or created'
    )
    claude_response = fields.Text(
        string='Claude Response',
        readonly=True,
        help='Raw response received from Claude AI'
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Error message if something went wrong during the process'
    )

    def process_prompt(self):
        self.ensure_one()
        view = self.view_id
        current_arch = view.arch_db

        try:
            if self.is_edit_mode:
                prompt = self._prepare_edit_prompt(current_arch)
            else:
                prompt = self._prepare_prompt(current_arch)

            _logger.info(f"Prompt sent to Claude: {prompt}")

            claude_response = self.claude_api_call(prompt)
            _logger.info(f"Response received from Claude: {claude_response}")

            self.write({
                'claude_response': claude_response,
                'prompt_processing_date': fields.Datetime.now(),
                'state': 'processed'
            })

            if self.is_edit_mode:
                self._validate_and_update_view(claude_response, view)
            else:
                self._validate_and_create_view(claude_response, view)

        except Exception as e:
            error_message = f"Error in process_prompt: {str(e)}"
            _logger.exception(error_message)
            self.write({
                'error_message': error_message,
                'state': 'error',
                'prompt_processing_date': fields.Datetime.now()
            })
            raise UserError(_(error_message))

    def _prepare_prompt(self, current_arch):
        return f"""
        Modify this XML view according to the following instruction:
        {self.prompt}

        Current XML view:
        {current_arch}

        Important instructions:
        1. Return ONLY the XML code for a new inherited view that implements the requested changes.
        2. The inherited view must contain a root <odoo> element and within it a <record> element with id, model="ir.ui.view" attributes, and the fields name, model, inherit_id and arch.
        3. Inside the arch field, place the necessary xpath elements.
        4. Use appropriate XPath operations (after, before, inside, replace, attributes) as needed.
        5. You can include multiple XPath operations if necessary.
        6. Make sure all XML elements are properly closed.
        7. Do not include additional explanations, just the XML of the inherited view.

        Expected format example:
        <odoo>
            <record id="view_partner_form_inherited" model="ir.ui.view">
                <field name="name">res.partner.form.inherited</field>
                <field name="model">res.partner</field>
                <field name="inherit_id" ref="base.view_partner_form"/>
                <field name="arch" type="xml">
                    <xpath expr="//field[@name='name']" position="after">
                        <field name="new_field"/>
                    </xpath>
                    <xpath expr="//field[@name='email']" position="attributes">
                        <attribute name="required">1</attribute>
                    </xpath>
                </field>
            </record>
        </odoo>
        """

    def _prepare_edit_prompt(self, current_arch):
        return f"""
        Modify this XML view according to the following instruction:
        {self.prompt}

        Current XML view:
        {current_arch}

        Important instructions:
        1. Return ONLY the complete modified XML view.
        2. Preserve the root structure and all necessary attributes.
        3. Include ALL the original content with the requested modifications.
        4. Make sure all XML elements are properly closed.
        5. Do not include additional explanations, just the modified XML.
        6. The response should be a valid Odoo view architecture that can replace the current one.
        7. Preserve any existing groups, access rights, and other security-related attributes.

        Return the complete modified XML structure, starting with <?xml version="1.0"?>
        """

    def _validate_and_create_view(self, inherited_view_xml, original_view):
        try:
            _logger.info(f"XML received for validation: {inherited_view_xml}")
            self.validate_xml(inherited_view_xml)

            # Parse the inherited view XML
            root = etree.fromstring(inherited_view_xml)
            record = root.find(".//record[@model='ir.ui.view']")

            if record is None:
                raise UserError(_("The XML does not contain a valid view record"))

            # Extract necessary values from XML
            name = record.find(".//field[@name='name']").text
            model = record.find(".//field[@name='model']").text
            inherit_id_ref = record.find(".//field[@name='inherit_id']").get('ref')
            arch = record.find(".//field[@name='arch']")

            # Extract xpath elements
            xpath_elements = arch.findall('.//xpath')

            # Create inherited view content
            arch_content = '<?xml version="1.0"?>\n<data>\n'
            for xpath in xpath_elements:
                arch_content += '    ' + etree.tostring(xpath, encoding='unicode', pretty_print=True)
            arch_content += '</data>'

            # Create the new view
            new_view = self.env['ir.ui.view'].create({
                'name': name,
                'model': model,
                'inherit_id': self.env.ref(inherit_id_ref).id,
                'arch_db': arch_content,
                'priority': 99,
            })

            self.write({
                'result': f"New inherited view created with ID: {new_view.id}",
                'state': 'applied',
                'view_update_date': fields.Datetime.now()
            })

        except Exception as e:
            error_message = f"Error validating or creating view: {str(e)}\nReceived XML: {inherited_view_xml}"
            self.write({
                'error_message': error_message,
                'state': 'error'
            })
            _logger.exception("Error validating or creating view")
            raise UserError(_(error_message))

    def _validate_and_update_view(self, modified_xml, view):
        try:
            _logger.info(f"XML received for validation: {modified_xml}")
            self.validate_xml(modified_xml)

            # Update the existing view
            view.write({
                'arch_db': modified_xml
            })

            self.write({
                'result': f"View updated successfully: {view.id}",
                'state': 'applied',
                'view_update_date': fields.Datetime.now()
            })

        except Exception as e:
            error_message = f"Error validating or updating view: {str(e)}\nReceived XML: {modified_xml}"
            self.write({
                'error_message': error_message,
                'state': 'error'
            })
            _logger.exception("Error validating or updating view")
            raise UserError(_(error_message))

    @api.model
    def validate_xml(self, xml_string):
        try:
            etree.fromstring(xml_string)
        except etree.XMLSyntaxError as e:
            raise UserError(_("Invalid XML: %s") % str(e))

    @api.model
    def claude_api_call(self, prompt):
        api_key = self.env['ir.config_parameter'].sudo().get_param('debug_ai.api_key')
        if not api_key:
            raise UserError(_("Debug AI API Key not configured. Please set it in Settings."))

        api_url = "https://api.anthropic.com/v1/messages"
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": api_key
        }
        data = {
            "model": "claude-3-5-sonnet-20240620",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
            "stream": True
        }

        try:
            _logger.info(f"Sending request to Claude API: {json.dumps(data)}")
            response = requests.post(api_url, headers=headers, json=data, stream=True)
            _logger.info(f"Response status code: {response.status_code}")

            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[6:]
                        try:
                            event_data = json.loads(json_str)
                            if event_data['type'] == 'content_block_delta':
                                if 'text' in event_data['delta']:
                                    full_response += event_data['delta']['text']
                            elif event_data['type'] == 'message_delta':
                                if 'stop_reason' in event_data['delta']:
                                    _logger.info(f"Stream stopped: {event_data['delta']['stop_reason']}")
                            elif event_data['type'] == 'error':
                                raise UserError(_(f"API Error: {event_data['error']}"))
                        except json.JSONDecodeError:
                            _logger.warning(f"Failed to decode JSON: {json_str}")

            _logger.info(f"Complete response from Claude API: {full_response}")

            if not full_response.strip():
                _logger.warning("Claude API response is empty.")
                raise UserError(_("Claude API response is empty. Please check the prompt or try again."))

            return full_response.strip()

        except requests.RequestException as e:
            error_message = f"API call error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_message += f"\nStatus code: {e.response.status_code}"
                error_message += f"\nResponse content: {e.response.text}"
            _logger.error(error_message)
            raise UserError(_(error_message))
        except json.JSONDecodeError as e:
            _logger.error(f"Error decoding JSON response: {str(e)}")
            raise UserError(_("Error decoding API response"))
        except Exception as e:
            _logger.exception("Unexpected error in claude_api_call")
            raise UserError(_("Unexpected error: %s") % str(e))

    def apply_changes(self):
        self.ensure_one()
        if self.state == 'processed' and self.result and "New inherited view created with ID:" in self.result:
            self.write({
                'state': 'applied',
                'applied_date': fields.Datetime.now()
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.ref('debug_ai.menu_debug_ai').id,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No changes to apply or there was an error in the process.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    claude_api_key = fields.Char(string="Debug AI API Key", config_parameter='debug_ai.api_key')
