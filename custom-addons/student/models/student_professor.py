# This model defines professors in the PaLMS system.
# Professors can be linked to faculties, scientific profiles, and offer student projects.
# It tracks their activity, commission involvement, and related user account.

from odoo import api, fields, models


class Professor(models.Model):
    _name = "student.professor"
    _description = "PaLMS - Professors"

    # Name of the professor, computed from linked user account
    name = fields.Char(
        'Professor Name',
        required=True,
        default=lambda self: self.env.user.name,
        compute="_compute_name",
        store=True,
        readonly=True
    )

    # Whether the professor is active in the system
    active = fields.Boolean(default=True)

    # Timestamp of last login or activity
    last_seen = fields.Datetime("Last Seen", default=lambda self: fields.Datetime.now())

    # Indicates if the professor is a visiting faculty
    visiting_professor = fields.Boolean('Visiting professor?', default=False)

    # Scientific research profiles associated with the professor
    scientific_profile_ids = fields.Many2many(
        'student.scientific_profile',
        string='Scientific profile'
    )

    # Short biography or additional info
    about = fields.Text("About the Professor")

    # User account linked to the professor profile
    professor_account = fields.Many2one(
        'res.users',
        string='User Account',
        default=lambda self: self.env.user,
        required=True
    )

    # Faculty to which the professor is assigned
    professor_faculty = fields.Many2one('student.faculty', string='Faculty', required=True)

    # List of offered student projects (excluding ineligible)
    project_ids = fields.One2many(
        'student.project',
        'professor_id',
        string='Projects',
        domain=[('state_publication', '!=', 'ineligible')]
    )

    # Number of commissions the professor is part of
    number_of_commissions = fields.Integer(
        "Number of Commissions",
        compute='_compute_number_of_commissions',
        store=True,
        readonly=True
    )

    # Compute number of commissions
    def compute_number_of_commissions(self):
        for professor in self:
            count = self.env['student.commission'].search_count([
                ('professor_ids', 'in', professor.id)
            ])
            professor.number_of_commissions = count

    # Compute name from user account
    @api.depends("professor_account")
    def _compute_name(self):
        for record in self:
            record.name = record.professor_account.name

    # Number of visible (published) student projects offered
    offered_projects = fields.Integer(
        string='Number of Published Projects',
        compute='_compute_project_count',
        store=True,
        readonly=True
    )

    # Automatically update related faculty on user change
    @api.onchange("professor_account")
    def _set_professor_faculty(self):
        self.professor_account.faculty = self.professor_faculty

    # SQL constraint to ensure valid data
    _sql_constraints = [
        ('check_offered_projects', 'CHECK(offered_projects >= 0)', 'The number of offered projects can\'t be negative.'),
    ]

    # Compute number of published student projects
    @api.depends('project_ids')
    @api.model
    def _compute_project_count(self):
        for professor in self:
            professor.offered_projects = len(professor.project_ids)

    # Button action to view all projects offered by this professor
    def action_view_professor_projects(self):
        action = self.env.ref('student.action_project').sudo().read()[0]
        action['domain'] = [('professor_id', '=', self.id)]
        return action