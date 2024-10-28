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
import html
import re
import requests
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DebugAI(models.Model):
    _name = 'debug.ai'
    _description = 'Debug AI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    model_id = fields.Many2one('ir.model', string='Model', required=False, ondelete='cascade', tracking=True)
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
            "model": "claude-3-5-sonnet-20241022",
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

    @api.model
    def claude_api_call_html(self, prompt):
        """Llamada al API de Claude con mejor manejo de errores"""
        try:
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
                "model": "claude-3-5-sonnet-20241022",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8000,
                "stream": True
            }

            _logger.info("Sending request to Claude API")
            response = requests.post(api_url, headers=headers, json=data, stream=True)
            response.raise_for_status()

            full_text = ""
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    decoded_line = line.decode('utf-8')
                    if not decoded_line.startswith('data: '):
                        continue

                    event_data = json.loads(decoded_line[6:])
                    if event_data.get('type') == 'content_block_delta':
                        if 'text' in event_data.get('delta', {}):
                            full_text += event_data['delta']['text']

                except json.JSONDecodeError as e:
                    _logger.warning(f"Error decoding JSON from Claude: {e}")
                    continue
                except Exception as e:
                    _logger.warning(f"Unexpected error processing Claude response line: {e}")
                    continue

            if not full_text.strip():
                raise UserError(_("Claude API response is empty. Please check the prompt or try again."))

            # Procesar el texto completo
            return self._format_response(full_text)

        except requests.RequestException as e:
            error_message = f"API call error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_message += f"\nStatus code: {e.response.status_code}"
                error_message += f"\nResponse content: {e.response.text}"
            _logger.error(error_message)
            raise UserError(_(error_message))
        except Exception as e:
            _logger.exception("Unexpected error in claude_api_call")
            error_message = f"Unexpected error: {str(e)}"
            raise UserError(_(error_message))

    def _format_response(self, text):
        """
        Formatea la respuesta de Claude en HTML con estilo apropiado
        """
        try:
            # Usamos un delimitador único que sea muy improbable que aparezca en el texto
            TEMP_CODE_START = "<<CLAUDE_CODE_BLOCK_START>>"
            TEMP_CODE_END = "<<CLAUDE_CODE_BLOCK_END>>"

            # Primera fase: reemplazar los delimitadores de código
            text = text.replace('```', TEMP_CODE_START, 1)  # Primera ocurrencia
            while '```' in text:
                text = text.replace('```', TEMP_CODE_END, 1)  # Siguiente ocurrencia
                if '```' in text:
                    text = text.replace('```', TEMP_CODE_START, 1)  # Y la siguiente, si existe

            # Si quedó algún delimitador sin cerrar, lo cerramos
            if text.count(TEMP_CODE_START) > text.count(TEMP_CODE_END):
                text += TEMP_CODE_END

            # Segunda fase: dividir y procesar el texto
            parts = []
            current_text = text
            while TEMP_CODE_START in current_text:
                # Encontrar el próximo bloque de código
                pre_code, rest = current_text.split(TEMP_CODE_START, 1)

                # Procesar el texto antes del código
                if pre_code.strip():
                    parts.append(('text', pre_code))

                # Procesar el bloque de código
                if TEMP_CODE_END in rest:
                    code, current_text = rest.split(TEMP_CODE_END, 1)
                    parts.append(('code', code))
                else:
                    # Si no hay delimitador de fin, tratar todo como código
                    parts.append(('code', rest))
                    current_text = ''

            # Procesar cualquier texto restante
            if current_text.strip():
                parts.append(('text', current_text))

            # Tercera fase: formatear cada parte
            formatted_parts = []
            for part_type, content in parts:
                if part_type == 'text':
                    formatted_parts.append(self._process_regular_text(content))
                else:  # code
                    formatted_parts.append(self._process_code_block(content))

            # Unir todo y envolver en el contenedor principal
            result = '\n'.join(formatted_parts)
            return f'<div class="claude-response">{result}</div>'

        except Exception as e:
            _logger.error(f"Error formatting response: {e}")
            return f'<div class="claude-response"><pre>{html.escape(text)}</pre></div>'

    def _process_regular_text(self, text):
        """
        Procesa el texto regular (no código)
        """
        try:
            paragraphs = text.strip().split('\n')
            formatted_paragraphs = []
            current_list_type = None

            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue

                # Procesar listas numeradas
                if re.match(r'^\d+\.\s', p):
                    if current_list_type != 'ol':
                        if current_list_type:
                            formatted_paragraphs.append(f'</{current_list_type}>')
                        formatted_paragraphs.append('<ol>')
                        current_list_type = 'ol'
                    list_content = p.split('. ', 1)
                    content = list_content[1] if len(list_content) > 1 else p
                    formatted_paragraphs.append(f'<li>{content}</li>')

                # Procesar viñetas
                elif p.startswith('- '):
                    if current_list_type != 'ul':
                        if current_list_type:
                            formatted_paragraphs.append(f'</{current_list_type}>')
                        formatted_paragraphs.append('<ul>')
                        current_list_type = 'ul'
                    formatted_paragraphs.append(f'<li>{p[2:]}</li>')

                else:
                    # Cerrar lista si estábamos en una
                    if current_list_type:
                        formatted_paragraphs.append(f'</{current_list_type}>')
                        current_list_type = None

                    # Procesar encabezados
                    if p.startswith('#'):
                        heading_match = re.match(r'^(#{1,6})\s+(.+)$', p)
                        if heading_match:
                            level = len(heading_match.group(1))
                            content = heading_match.group(2)
                            formatted_paragraphs.append(f'<h{level}>{content}</h{level}>')
                    else:
                        # Procesar negrita e itálica
                        p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p)
                        p = re.sub(r'\*(.*?)\*', r'<em>\1</em>', p)
                        formatted_paragraphs.append(f'<p>{p}</p>')

            # Cerrar cualquier lista abierta
            if current_list_type:
                formatted_paragraphs.append(f'</{current_list_type}>')

            return '\n'.join(formatted_paragraphs)
        except Exception as e:
            _logger.warning(f"Error processing regular text: {e}")
            return f'<p>{html.escape(text)}</p>'

    def _process_code_block(self, text):
        """
        Procesa un bloque de código
        """
        try:
            lines = text.strip().split('\n')
            if not lines:
                return ''

            # Detectar lenguaje
            first_line = lines[0].strip().lower()
            known_languages = {
                'python', 'javascript', 'js', 'html', 'css', 'xml', 'sql',
                'bash', 'shell', 'php', 'ruby', 'java', 'cpp', 'c++', 'c',
                'typescript', 'ts', 'json', 'yaml', 'markdown', 'md'
            }

            if first_line in known_languages:
                lang = first_line
                code = '\n'.join(lines[1:])
            else:
                lang = ''
                code = '\n'.join(lines)

            lang_attr = f' class="language-{lang}"' if lang else ''
            return f'<pre class="code-block"><code{lang_attr}>{html.escape(code.strip())}</code></pre>'
        except Exception as e:
            _logger.warning(f"Error processing code block: {e}")
            return f'<pre class="code-block"><code>{html.escape(text)}</code></pre>'

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
