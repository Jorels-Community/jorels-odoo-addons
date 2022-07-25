# -*- coding: utf-8 -*-
#
#   l10n_co_edi_jorels
#   Copyright (C) 2022  Jorels SAS
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#   email: info@jorels.com
#

# First load configuration
from . import config
from . import listings

# Then load other models
from . import res_partner
from . import account_move
from . import account_move_line
from . import account_move_reversal
from . import account_debit_note
from . import mail_message
from . import mail_template
from . import radian
