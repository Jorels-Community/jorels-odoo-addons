import fnmatch
import logging
import os
from typing import Optional, Tuple

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.modules import module
from pathlib import Path

_logger = logging.getLogger(__name__)


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

    analysis_result = fields.Html(
        string='Analysis Result',
        readonly=True,
        tracking=True,
        sanitize=True
    )

    prompt_result = fields.Html(
        string='Prompt Result',
        readonly=True,
        sanitize=True,  # Desactivar sanitización
        strip_classes=False,  # Mantener clases CSS
        strip_style=False,  # Mantener estilos inline
    )

    prompt_request = fields.Text('Prompt request')

    def _get_module_path(self):
        module_name = self.technical_name
        module_path = module.get_module_path(module_name)
        return module_path


    def _get_temp_file_path(self):
        """Get temporary file path"""
        return f'/tmp/odoo_debug_ai_{self.id}.prompt'

    def _clean_up_resources(self, debug_ai=None, temp_file=None):
        """Clean up temporary resources"""
        if debug_ai:
            try:
                debug_ai.unlink()
            except Exception as e:
                _logger.error(f"Error al eliminar debug_ai: {str(e)}")

        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                _logger.error(f"Error al eliminar archivo temporal: {str(e)}")

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

    def _generate_and_read_prompt(self, problem_description: str) -> Tuple[str, str]:
        """
        Generate and read prompt content for module analysis.

        Args:
            problem_description: Description of the problem to analyze

        Returns:
            Tuple containing (prompt_content, temp_file_path)

        Raises:
            UserError: If there's an error reading the generated prompt
        """

        output_file = self._get_temp_file_path()
        module_path = self._get_module_path()

        _logger.info(f"Generating prompt for module {self.technical_name}")
        OdooModuleToPrompt().prompt(module_path, output_file, problem_description)

        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return f.read(), output_file
        except Exception as e:
            if os.path.exists(output_file):
                os.remove(output_file)
            raise UserError(_('Error reading generated prompt: %s') % str(e))

    def _process_with_claude(self, prompt_content):
        """Process the prompt with Claude AI"""
        debug_ai = None
        try:
            debug_ai = self.env['debug.ai'].create({
                'name': f'Module Analysis Prompt - {self.technical_name}',
                'prompt': prompt_content,
                'view_id': self.env.ref('base.view_view_form').id,  # Required field
                'state': 'draft'
            })

            _logger.info(f"Sending prompt to Claude for module {self.technical_name}")
            return debug_ai.claude_api_call_html(prompt_content), debug_ai

        except Exception as e:
            if debug_ai:
                debug_ai.unlink()
            raise UserError(_('Error processing with Claude: %s') % str(e))

    def action_prompt_module(self):
        """Execute module prompt and store results"""
        self.ensure_one()
        debug_ai = None
        temp_file = None

        try:
            # Problem description
            problem_description = self.prompt_request

            # Generate and read prompt
            prompt_content, temp_file = self._generate_and_read_prompt(problem_description)

            # Process with Claude
            claude_response, debug_ai = self._process_with_claude(prompt_content)

            # Update record
            self.write({
                'analysis_date': fields.Datetime.now(),
                'prompt_result': claude_response,
                'state': 'done'
            })

            # Clean up resources
            self._clean_up_resources(debug_ai, temp_file)

            return True

        except Exception as e:
            # Clean up in case of error
            self._clean_up_resources(debug_ai, temp_file)

            self.write({
                'analysis_date': fields.Datetime.now(),
                'prompt_result': str(e),
                'state': 'error'
            })
            raise UserError(_('Error in module prompt: %s') % str(e))

    def _perform_module_analysis(self):
        """Analyze module dependencies"""
        self.ensure_one()
        module = self.module_id
        result = []

        deps = module.dependencies_id
        result.append(f"\nDependencies: {len(deps)}")
        for dep in deps:
            result.append(f"- {dep.name}")

        return '\n'.join(result)


class FileReader:
    @staticmethod
    def read_file(file_path: str, max_lines: Optional[int] = None) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"No read permission for file: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            if max_lines:
                return ''.join(file.readline() for _ in range(max_lines))
            return file.read()


class GitignoreHandler:
    @staticmethod
    def parse_gitignore(gitignore_path):
        """Parse .gitignore file and return list of patterns"""
        if not os.path.exists(gitignore_path):
            return []

        patterns = []
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Convertir patrones relativos a absolutos
                    if not line.startswith('/'):
                        line = f'**/{line}'
                    if line.endswith('/'):
                        line = f'{line}**'
                    patterns.append(line)
        return patterns

    @staticmethod
    def should_ignore(file_path, patterns):
        """Check if file should be ignored based on gitignore patterns"""
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False


class ModuleProcessor:
    def __init__(self, directory):
        self.directory = directory
        self.gitignore_patterns = []
        gitignore_path = os.path.join(directory, '.gitignore')
        if os.path.exists(gitignore_path):
            self.gitignore_patterns = GitignoreHandler.parse_gitignore(gitignore_path)

    def should_process_path(self, path):
        """Check if a path should be processed"""
        relative_path = os.path.relpath(path, self.directory)
        return not GitignoreHandler.should_ignore(relative_path, self.gitignore_patterns)

    def process_directory(self):
        content = []

        for root, dirs, files in os.walk(self.directory):
            # Filtrar directorios
            dirs[:] = [d for d in dirs if self.should_process_path(os.path.join(root, d))]

            # Procesar archivos
            for file in files:
                file_path = os.path.join(root, file)
                if not self.should_process_path(file_path):
                    continue

                if file.endswith(('.py', '.xml', '.csv', '.js')) and file != '.gitignore':
                    relative_path = os.path.relpath(file_path, self.directory)

                    try:
                        if file.endswith('.csv'):
                            file_content = FileReader.read_file(file_path, max_lines=100)
                        else:
                            file_content = FileReader.read_file(file_path)

                        content.append(f"File: {relative_path}\n\n```\n{file_content}\n```\n\n")
                    except Exception as e:
                        _logger.warning(f"Error reading file {file_path}: {str(e)}")

        return '\n'.join(content)


class PromptCreator:
    def __init__(self, module_path, problem_description):
        self.module_path = module_path
        self.module_name = os.path.basename(module_path)
        self.processor = ModuleProcessor(module_path)
        self.problem_description = problem_description

    def create_prompt(self):
        content = self.processor.process_directory()
        prompt = f"""
This is the content of the Odoo module '{self.module_name}', excluding files and folders specified in .gitignore. For CSV files, a maximum of 100 lines are shown. Please analyze the code and structure of the module:

{content}

Based on this code, please solve the following problem:

{self.problem_description}
"""
        return prompt


class OdooModuleToPrompt:
    @staticmethod
    def prompt(module_path, output_file, problem_description):
        abs_module_path = os.path.abspath(module_path)
        prompt_creator = PromptCreator(abs_module_path, problem_description)
        prompt = prompt_creator.create_prompt()

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(prompt)

        _logger.info(f"Prompt generated and saved in {output_file}")
