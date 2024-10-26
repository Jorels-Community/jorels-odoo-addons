from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ModuleAnalysis(models.Model):
    _name = 'debug_ai.module.analysis'
    _description = 'Module Analysis'
    _rec_name = 'module_id'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    module_id = fields.Many2one(
        'ir.module.module',
        string='Module',
        required=True,
        domain=[('state', '=', 'installed')],
        ondelete='cascade',
        tracking=True
    )

    technical_name = fields.Char(
        related='module_id.name',
        string='Technical Name',
        store=True
    )

    version = fields.Char(
        related='module_id.latest_version',
        string='Version',
        store=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Analyzed'),
        ('error', 'Error')
    ], default='draft', string='State', tracking=True)

    analysis_date = fields.Datetime(
        string='Analysis Date',
        readonly=True,
        tracking=True
    )

    analysis_result = fields.Text(
        string='Analysis Result',
        readonly=True,
        tracking=True
    )

    def action_analyze_module(self):
        """Execute module analysis and store results"""
        self.ensure_one()
        try:
            result = self._perform_module_analysis()

            self.write({
                'analysis_date': fields.Datetime.now(),
                'analysis_result': result,
                'state': 'done'
            })
        except Exception as e:
            self.write({
                'analysis_date': fields.Datetime.now(),
                'analysis_result': str(e),
                'state': 'error'
            })
            raise UserError(_('Error analyzing module: %s') % str(e))

    def _perform_module_analysis(self):
        self.ensure_one()
        module = self.module_id
        result = []

        # Analyze module models
        models = self.env['ir.model'].search([('modules', 'like', module.name)])
        result.append(f"Models found: {len(models)}")
        for model in models:
            result.append(f"- {model.name} ({model.model})")

        # Analyze module views
        views = self.env['ir.ui.view'].search([('name', 'like', module.name)])
        result.append(f"\nViews found: {len(views)}")

        # Analyze dependencies
        deps = module.dependencies_id
        result.append(f"\nDependencies: {len(deps)}")
        for dep in deps:
            result.append(f"- {dep.name}")

        return '\n'.join(result)