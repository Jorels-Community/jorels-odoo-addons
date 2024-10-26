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

import logging

from odoo import models, fields, _
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
            'model_id': self.env['ir.model']._get(self.model).id if self.model else None,
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
            'model_id': self.env['ir.model']._get(self.model).id if self.model else None,
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
