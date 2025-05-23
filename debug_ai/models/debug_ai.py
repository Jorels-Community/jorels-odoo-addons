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

import markdown
import anthropic
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
        """
        Process a prompt by sending it to Claude API and handling the response.

        This function prepares a prompt based on the current view architecture,
        sends it to the Claude API, and processes the response. It can operate
        in two modes:
        - Edit mode: Updates an existing view with Claude's suggestions
        - Create mode: Creates a new view based on Claude's response

        The function handles all API communication, logging, and error management.

        Returns:
            None

        Raises:
            UserError: If any exception occurs during prompt processing
        """
        self.ensure_one()
        view = self.view_id
        current_arch = view.arch_db

        try:
            if self.is_edit_mode:
                # Prepare a prompt for editing an existing view
                prompt = self._prepare_edit_prompt(current_arch)
            else:
                # Prepare a prompt for creating a new view
                prompt = self._prepare_prompt(current_arch)

            _logger.debug(f"Prompt sent to Claude: {prompt}")

            # Make the API call to Claude
            claude_response = self.claude_api_call(prompt)
            _logger.debug(f"Response received from Claude: {claude_response}")

            # Update record with the response data
            self.write({
                'claude_response': claude_response,
                'prompt_processing_date': fields.Datetime.now(),
                'state': 'processed'
            })

            if self.is_edit_mode:
                # Validate and update the existing view
                self._validate_and_update_view(claude_response, view)
            else:
                # Validate and create a new view
                self._validate_and_create_view(claude_response, view)

        except Exception as e:
            # Log and handle any errors
            error_message = f"Error in process_prompt: {str(e)}"
            _logger.error(error_message)
            self.write({
                'error_message': error_message,
                'state': 'error',
                'prompt_processing_date': fields.Datetime.now()
            })
            raise UserError(_(error_message))

    def _prepare_prompt(self, current_arch):
        """
        Prepare a prompt for creating a new inherited view in Odoo.

        This function generates a structured prompt to send to Claude API,
        requesting the creation of a new inherited view based on the user's
        instructions and the current view architecture.

        The prompt includes:
        - The user's instruction for modifying the view
        - The current XML architecture of the view
        - Important guidelines for creating a proper inherited view
        - An example of the expected format for the response

        Args:
            current_arch (str): The XML architecture of the current view

        Returns:
            str: A formatted prompt string to send to Claude API
        """
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
        """
        Prepare a prompt for directly editing an existing Odoo view.

        This function generates a structured prompt to send to Claude API,
        requesting modifications to an existing view based on the user's
        instructions. Unlike _prepare_prompt which creates an inherited view,
        this function asks for a complete replacement of the current view.

        The prompt includes:
        - The user's instruction for modifying the view
        - The current XML architecture of the view
        - Important guidelines for preserving the structure while making changes
        - Instructions to return the complete modified XML

        Args:
            current_arch (str): The XML architecture of the current view

        Returns:
            str: A formatted prompt string to send to Claude API
        """
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
        """
        Validate and create a new inherited view in Odoo based on XML generated by Claude.

        This function performs the following steps:
        1. Validates the XML structure
        2. Parses the XML to extract necessary fields (name, model, inherit_id, and arch)
        3. Processes the XPath elements to create proper arch content
        4. Creates a new inherited view in the database
        5. Updates the record state to 'applied' upon success

        The function handles both the validation and creation process, ensuring
        that the XML provided by Claude is properly transformed into a valid
        Odoo inherited view.

        Args:
            inherited_view_xml (str): The XML for the inherited view provided by Claude
            original_view (ir.ui.view): The original view being inherited from

        Returns:
            None

        Raises:
            UserError: If validation fails or view creation encounters an error
        """
        try:
            _logger.debug(f"XML received for validation: {inherited_view_xml}")
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
            _logger.error("Error validating or creating view")
            raise UserError(_(error_message))

    def _validate_and_update_view(self, modified_xml, view):
        """
        Validate and update an existing Odoo view with modified XML from Claude.

        This function performs the following steps:
        1. Validates the XML structure for correctness
        2. Updates the existing view's architecture with the new XML
        3. Updates the record state to 'applied' upon success

        Unlike _validate_and_create_view which creates a new inherited view,
        this function directly modifies an existing view's architecture.
        This is typically used when editing a view rather than creating
        an inheritance chain.

        Args:
            modified_xml (str): The modified XML for the view provided by Claude
            view (ir.ui.view): The existing view to be updated

        Returns:
            None

        Raises:
            UserError: If validation fails or view update encounters an error
        """
        try:
            _logger.debug(f"XML received for validation: {modified_xml}")
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
            _logger.error("Error validating or updating view")
            raise UserError(_(error_message))

    @api.model
    def validate_xml(self, xml_string):
        """
        Validate that a string is well-formed XML.

        This model-level method checks if the provided string can be parsed as
        valid XML. It attempts to parse the XML using lxml's etree and raises
        a user-friendly error if the parsing fails.

        This is a key validation step before attempting to create or update
        views with XML content generated by Claude, ensuring that only
        well-formed XML reaches the Odoo view system.

        Args:
            xml_string (str): The XML string to validate

        Returns:
            None

        Raises:
            UserError: If the XML is invalid, with a descriptive error message
        """
        try:
            etree.fromstring(xml_string)
        except etree.XMLSyntaxError as e:
            raise UserError(_("Invalid XML: %s") % str(e))

    @api.model
    def claude_api_call(self, prompt):
        """
        Make a streaming API call to Anthropic's Claude AI service using the official client.

        This model-level method handles the complete API communication process with
        Anthropic's Claude API using the official anthropic Python library, including:
        1. Retrieving the API key from Odoo's system parameters
        2. Creating an Anthropic client instance
        3. Making a streaming request to the Claude API
        4. Processing the streamed response incrementally using the official client
        5. Handling various error conditions and providing informative error messages

        The method uses streaming to process potentially large responses efficiently,
        using the official client's stream handling which is more robust than manual parsing.

        Args:
            prompt (str): The prompt text to send to Claude

        Returns:
            str: The complete text response from Claude

        Raises:
            UserError: If the API key is not configured, if the API returns an error,
                      if the response is empty, or if any other errors occur during
                      the API communication process
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('debug_ai.api_key')
        if not api_key:
            raise UserError(_("Debug AI API Key not configured. Please set it in Settings."))

        try:
            client = anthropic.Anthropic(api_key=api_key)

            _logger.debug("Sending streaming request to Claude API")

            full_response = ""
            with client.messages.stream(
                    max_tokens=8192,
                    messages=[{"role": "user", "content": prompt}],
                    model="claude-sonnet-4-20250514",
            ) as stream:
                for text in stream.text_stream:
                    full_response += text

            _logger.info(f"Complete response from Claude API received")

            if not full_response.strip():
                _logger.warning("Claude API response is empty.")
                raise UserError(_("Claude API response is empty. Please check the prompt or try again."))

            return full_response.strip()

        except anthropic.APIError as e:
            error_message = f"Anthropic API Error: {str(e)}"
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.AuthenticationError as e:
            error_message = f"Authentication Error: {str(e)}. Please check your API key."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.RateLimitError as e:
            error_message = f"Rate Limit Error: {str(e)}. Please try again later."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except Exception as e:
            _logger.exception("Unexpected error in claude_api_call")
            raise UserError(_("Unexpected error: %s") % str(e))

    @api.model
    def claude_api_call_html(self, prompt):
        """
        Make a streaming API call to Anthropic's Claude AI service with HTML formatting.

        This model-level method is an enhanced version of claude_api_call that includes:
        1. Integration with the official Anthropic client library
        2. Cleaner stream processing using the official client
        3. Use of debug-level logging for detailed API communication
        4. Integration with a response formatter via _format_response method
        5. Support for the latest Claude 3.5 Sonnet model

        The method processes the streamed response from Claude incrementally,
        building the complete response while handling potential errors at each step.
        After collecting the full response, it passes it through a formatter method
        that converts plain text to HTML.

        Args:
            prompt (str): The prompt text to send to Claude

        Returns:
            str: The formatted response from Claude, processed by _format_response

        Raises:
            UserError: If the API key is not configured, if the API returns an error,
                      if the response is empty, or if any other errors occur during
                      the API communication process
        """
        try:
            api_key = self.env['ir.config_parameter'].sudo().get_param('debug_ai.api_key')
            if not api_key:
                raise UserError(_("Debug AI API Key not configured. Please set it in Settings."))

            client = anthropic.Anthropic(api_key=api_key)

            _logger.debug("Sending streaming request to Claude API")

            full_text = ""
            with client.messages.stream(
                    max_tokens=8192,
                    messages=[{"role": "user", "content": prompt}],
                    model="claude-sonnet-4-20250514",
            ) as stream:
                for text in stream.text_stream:
                    full_text += text

            if not full_text.strip():
                raise UserError(_("Claude API response is empty. Please check the prompt or try again."))

            # Procesar el texto completo
            return self._format_response(full_text)

        except anthropic.APIError as e:
            error_message = f"Anthropic API Error: {str(e)}"
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.AuthenticationError as e:
            error_message = f"Authentication Error: {str(e)}. Please check your API key."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.RateLimitError as e:
            error_message = f"Rate Limit Error: {str(e)}. Please try again later."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except Exception as e:
            _logger.exception("Unexpected error in claude_api_call")
            error_message = f"Unexpected error: {str(e)}"
            raise UserError(_(error_message))

    def _format_response(self, text):
        """
        Format Claude's text response as HTML using Markdown processing.

        This method converts the plain text response from Claude into rich HTML content
        by applying Markdown rendering with multiple extensions. It enhances the
        presentation of the response by supporting various formatting elements like:

        - Code blocks with syntax highlighting
        - Tables
        - Definition lists
        - Footnotes
        - Table of contents
        - Smart typography
        - And more

        The method wraps the final HTML in a div with class 'claude-response' to allow
        for consistent styling in the Odoo UI. If any error occurs during the Markdown
        processing, it falls back to displaying the raw text within a pre tag to ensure
        the content is still visible to the user.

        Args:
            text (str): The plain text response from Claude to be formatted

        Returns:
            str: HTML-formatted content wrapped in a div with appropriate class
        """
        try:
            # Configurar las extensiones de markdown
            md = markdown.Markdown(extensions=[
                'fenced_code',  # Para bloques de código con ```
                'codehilite',  # Para resaltado de sintaxis
                'tables',  # Para tablas
                'attr_list',  # Para atributos HTML
                'def_list',  # Para listas de definición
                'footnotes',  # Para notas al pie
                'md_in_html',  # Para markdown dentro de HTML
                'sane_lists',  # Para listas más predecibles
                'smarty',  # Para comillas inteligentes
                'toc',  # Para tabla de contenidos
            ])

            # Convertir el texto a HTML
            html_content = md.convert(text)

            # Envolver en el contenedor con clase
            return f'<div class="claude-response">{html_content}</div>'

        except Exception as e:
            _logger.error(f"Error formatting response: {e}")
            return f'<div class="claude-response"><pre>{text}</pre></div>'

    def apply_changes(self):
        """
        Apply the changes after a successful view creation process.

        This method is typically called from a button in the UI after Claude has
        processed a request to create a new inherited view. It performs the following steps:

        1. Verifies that the current record has been processed successfully
        2. Checks if a new inherited view was actually created (by checking the result string)
        3. Updates the record state to 'applied' and sets the application timestamp
        4. Returns an action to reload the UI or display a notification depending on the result

        The method ensures proper UI feedback to the user - either reloading the view to
        show the applied changes or displaying a warning if there's nothing to apply.

        Returns:
            dict: Action dictionary for Odoo's client to either:
                  - Reload the UI and navigate to the Debug AI menu (on success)
                  - Display a warning notification (if no changes to apply)
        """
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

    @api.model
    def claude_api_call_with_history(self, messages):
        """
        Make a streaming API call to Claude AI with conversation history support.

        This model-level method enables multi-turn conversations with Claude by
        accepting an array of messages representing the conversation history.
        It handles the complete API communication process with Anthropic's Claude API
        using the official client library.

        Unlike claude_api_call which accepts a single prompt string, this method
        accepts a structured array of message objects in the format required by
        Claude's API (with role and content fields).

        Args:
            messages (list): A list of message objects with 'role' and 'content' keys
                             representing the conversation history

        Returns:
            str: The complete text response from Claude

        Raises:
            UserError: If the API key is not configured, if the API returns an error,
                      if the response is empty, or if any other errors occur during
                      the API communication process
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('debug_ai.api_key')
        if not api_key:
            raise UserError(_("Debug AI API Key not configured. Please set it in Settings."))

        try:
            client = anthropic.Anthropic(api_key=api_key)

            _logger.debug("Sending streaming request to Claude API with message history")

            full_text = ""
            with client.messages.stream(
                    max_tokens=8192,
                    messages=messages,
                    model="claude-sonnet-4-20250514",
            ) as stream:
                for text in stream.text_stream:
                    full_text += text

            if not full_text.strip():
                raise UserError(_("Claude API response is empty. Please check the prompt or try again."))

            return full_text.strip()

        except anthropic.APIError as e:
            error_message = f"Anthropic API Error: {str(e)}"
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.AuthenticationError as e:
            error_message = f"Authentication Error: {str(e)}. Please check your API key."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except anthropic.RateLimitError as e:
            error_message = f"Rate Limit Error: {str(e)}. Please try again later."
            _logger.error(error_message)
            raise UserError(_(error_message))
        except Exception as e:
            _logger.exception("Unexpected error in claude_api_call_with_history")
            error_message = f"Unexpected error: {str(e)}"
            raise UserError(_(error_message))
