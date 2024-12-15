import fnmatch
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.modules import module

_logger = logging.getLogger(__name__)


class ModuleAnalysisMessage(models.Model):
    _name = 'debug_ai.module.analysis.message'
    _description = 'Module Analysis Message History'
    _order = 'sequence, id'

    analysis_id = fields.Many2one(
        'debug_ai.module.analysis',
        string='Analysis',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant')
    ], string='Role', required=True)
    content = fields.Text('Content', required=True)
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now
    )


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

    prompt_result = fields.Text(
        string='Prompt Result',
        readonly=True,
    )

    # Agregar campo computado para visualización HTML
    prompt_result_html = fields.Html(
        string='Prompt Result HTML',
        compute='_compute_prompt_result_html',
        sanitize=True,
        strip_classes=False,
        strip_style=False,
    )

    prompt_request = fields.Text('Prompt request')

    message_history_ids = fields.One2many(
        'debug_ai.module.analysis.message',
        'analysis_id',
        string='Message History'
    )

    @api.depends('prompt_result')
    def _compute_prompt_result_html(self):
        for record in self:
            if record.prompt_result:
                record.prompt_result_html = self.env['debug.ai']._format_response(record.prompt_result)
            else:
                record.prompt_result_html = False

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

    def _process_with_claude(self, messages):
        """Process the prompt with Claude AI using message history"""
        debug_ai = None
        try:
            debug_ai = self.env['debug.ai'].create({
                'name': f'Module Analysis Prompt - {self.technical_name}',
                'prompt': messages[-1]['content'],  # último mensaje
                'view_id': self.env.ref('base.view_view_form').id,
                'state': 'draft'
            })

            _logger.info(f"Sending prompt to Claude for module {self.technical_name}")
            raw_response = debug_ai.claude_api_call_with_history(messages)

            # Verificar que la respuesta no sea None antes de devolverla
            if not raw_response:
                raise UserError(_('Empty response received from Claude API'))

            # Formatear la respuesta para visualización mientras mantenemos la versión raw
            formatted_response = debug_ai._format_response(raw_response)

            return formatted_response, debug_ai

        except Exception as e:
            if debug_ai:
                debug_ai.unlink()
            raise UserError(_('Error processing with Claude: %s') % str(e))

    def action_prompt_module(self):
        self.ensure_one()
        debug_ai = None
        temp_file = None

        try:
            # Problem description
            problem_description = self.prompt_request

            if not problem_description:
                raise UserError(_('Please provide a prompt request'))

            # Generate and read prompt
            prompt_content, temp_file = self._generate_and_read_prompt(problem_description)

            # Guardar el mensaje del usuario en el historial
            self.env['debug_ai.module.analysis.message'].create({
                'analysis_id': self.id,
                'role': 'user',
                'content': self.prompt_request,
                'sequence': len(self.message_history_ids) + 1
            })

            # Construir el historial de mensajes para Claude
            messages = []
            for msg in self.message_history_ids:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            messages.append({
                "role": "user",
                "content": prompt_content
            })

            # Process with Claude using message history
            formatted_response, debug_ai = self._process_with_claude(messages)

            # Obtener la respuesta raw para el historial
            raw_response = debug_ai.claude_api_call_with_history(messages)

            # Guardar la respuesta raw en el historial
            self.env['debug_ai.module.analysis.message'].create({
                'analysis_id': self.id,
                'role': 'assistant',
                'content': raw_response,
                'sequence': len(self.message_history_ids) + 1
            })

            # Update record con la respuesta formateada para visualización
            self.write({
                'analysis_date': fields.Datetime.now(),
                'prompt_result': formatted_response,
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
                    # Eliminar el slash inicial si existe, ya que manejaremos las rutas de forma relativa
                    if line.startswith('/'):
                        line = line[1:]
                    # Eliminar el slash final si existe
                    if line.endswith('/'):
                        line = line[:-1]
                    patterns.append(line)

        _logger.info(f"Parsed gitignore patterns: {patterns}")
        return patterns

    @staticmethod
    def should_ignore(file_path: str, patterns: list, module_root: str) -> bool:
        """
        Check if file should be ignored based on gitignore patterns
        """
        try:
            # Convertir rutas a Path objects para un manejo más robusto
            file_path = Path(file_path)
            module_root = Path(module_root)

            # Obtener la ruta relativa desde la raíz del módulo
            try:
                relative_path = file_path.relative_to(module_root)
                relative_str = str(relative_path).replace('\\', '/')  # Normalizar separadores
            except ValueError:
                _logger.error(f"File {file_path} is not relative to {module_root}")
                return False

            _logger.debug(f"Checking path: {relative_str} against patterns")

            # Comprobar cada patrón
            for pattern in patterns:
                # Verificar si el inicio de la ruta relativa coincide con el patrón
                path_parts = relative_str.split('/')
                current_path = ''

                for part in path_parts:
                    if current_path:
                        current_path += '/'
                    current_path += part

                    if fnmatch.fnmatch(current_path, pattern):
                        _logger.debug(f"Path {relative_str} matches pattern {pattern}")
                        return True

                    # También probar con el patrón como un prefijo directo
                    if current_path.startswith(pattern + '/'):
                        _logger.debug(f"Path {relative_str} starts with pattern {pattern}")
                        return True

            _logger.debug(f"Path {relative_str} does not match any pattern")
            return False

        except Exception as e:
            _logger.error(f"Error in should_ignore: {str(e)}")
            return False


class ModuleProcessor:
    def __init__(self, directory):
        self.directory = os.path.abspath(directory)
        self.gitignore_patterns = []
        gitignore_path = os.path.join(self.directory, '.gitignore')
        if os.path.exists(gitignore_path):
            self.gitignore_patterns = GitignoreHandler.parse_gitignore(gitignore_path)
            _logger.info(f"Initialized ModuleProcessor with gitignore patterns: {self.gitignore_patterns}")
        else:
            _logger.warning(f"No .gitignore file found at {gitignore_path}")

    def should_process_path(self, path: str) -> bool:
        """Check if a path should be processed"""
        try:
            should_ignore = GitignoreHandler.should_ignore(path, self.gitignore_patterns, self.directory)
            _logger.info(f"Checking path: {path} - Should ignore: {should_ignore}")
            return not should_ignore
        except Exception as e:
            _logger.error(f"Error in should_process_path: {str(e)}")
            return True

    def process_directory(self):
        _logger.info(f"Starting directory processing at: {self.directory}")
        content = []

        try:
            for root, dirs, files in os.walk(self.directory):
                # Primero verificar si el directorio actual debe ser ignorado
                relative_root = os.path.relpath(root, self.directory).replace('\\', '/')
                _logger.info(f"Processing directory: {relative_root}")

                if not self.should_process_path(root):
                    _logger.info(f"Skipping ignored directory: {relative_root}")
                    dirs[:] = []  # No procesar subdirectorios
                    continue

                # Filtrar directorios ignorados
                original_dirs = dirs.copy()
                dirs[:] = [d for d in dirs if self.should_process_path(os.path.join(root, d))]
                if len(dirs) != len(original_dirs):
                    _logger.info(f"Filtered out directories: {set(original_dirs) - set(dirs)}")

                # Procesar archivos
                for file in files:
                    if file == '.gitignore':
                        continue

                    file_path = os.path.join(root, file)
                    if not self.should_process_path(file_path):
                        _logger.info(f"Skipping ignored file: {os.path.relpath(file_path, self.directory)}")
                        continue

                    if file.endswith(('.py', '.xml', '.csv', '.js')):
                        relative_path = os.path.relpath(file_path, self.directory)
                        _logger.info(f"Processing file: {relative_path}")

                        try:
                            if file.endswith('.csv'):
                                file_content = FileReader.read_file(file_path, max_lines=100)
                            else:
                                file_content = FileReader.read_file(file_path)

                            content.append(f"File: {relative_path}\n\n```\n{file_content}\n```\n\n")
                        except Exception as e:
                            _logger.error(f"Error reading file {file_path}: {str(e)}")

        except Exception as e:
            _logger.error(f"Error processing directory: {str(e)}")

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
