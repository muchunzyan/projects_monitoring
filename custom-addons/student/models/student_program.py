# This model defines academic programs in PaLMS.
# Programs are categorized by degree level, language, length, and education type.
# Each program is linked to a faculty, supervisor, and manager, and tracks associated students and projects.

from odoo import fields, models, api

class Program(models.Model):
    _name = "student.program"
    _description = "PaLMS - Programs"

    # Program title
    name = fields.Char('Program Name', required=True, translate=True)

    # Academic degree type (e.g., Bachelor's, Master's, PhD)
    degree = fields.Selection([
        ('ba', "Bachelor's"),
        ('ms', "Master's"),
        ('phd', 'PhD')
    ], default='ba', string='Program Degree', required=True)

    # Language of instruction
    language = fields.Selection([
        ('en', 'English'),
        ('ru', 'Russian')
    ], default='ru', string='Language', required=True)

    # Duration of the program in years
    length = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6')
    ], default='4', string='Program Length', required=True)

    # Mode of delivery (Online, Offline, Hybrid)
    type = fields.Selection([
        ('on', 'Online'),
        ('off', 'Offline'),
        ('hrd', 'Hybrid')
    ], default='off', string='Mode of Education', required=True)

    # Link to the faculty this program belongs to
    program_faculty_id = fields.Many2one(
        'student.faculty',
        string='Faculty',
        default=lambda self: self.env['student.faculty'].search([], limit=1),
        required=True,
        store=True
    )

    # Academic supervisor of the program
    supervisor = fields.Many2one('student.supervisor', string='Academic Supervisor', required=True)

    # Administrative program manager
    manager = fields.Many2one('student.manager', string='Program Manager', required=True)

    # Number of enrolled students (computed)
    student_number = fields.Integer(
        string='Number of Students',
        compute='_compute_student_count',
        store=True,
        readonly=True
    )

    # List of students in the program
    student_ids = fields.One2many('student.student', 'student_program', string='Students')

    # Compute student count based on linked records
    @api.depends('student_ids')
    @api.model
    def _compute_student_count(self):
        self.student_number = len(self.student_ids)

    # Number of linked projects (computed)
    project_number = fields.Integer(
        string='Number of Projects',
        compute='_compute_project_count',
        store=True,
        readonly=True
    )

    # Many2many relation to projects visible for the program
    project_ids = fields.Many2many('student.project', string='Faculty Projects')

    # Compute number of projects
    @api.depends('project_ids')
    @api.model
    def _compute_project_count(self):
        self.project_number = len(self.project_ids)