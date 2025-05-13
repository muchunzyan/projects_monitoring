# This model defines academic supervisors in the PaLMS system.
# Supervisors oversee academic programs and are associated with faculties and user accounts.

from odoo import api, fields, models
from datetime import datetime, timedelta

class Supervisor(models.Model):
    _name = "student.supervisor"
    _description = "PaLMS - Supervisors"

    # Display name of the supervisor, computed from the linked user account
    name = fields.Char(
        'Supervisor Name',
        required=True,
        default=lambda self: self.env.user.name,
        compute="_compute_name",
        store=True,
        readonly=True
    )

    # Whether the supervisor is active
    active = fields.Boolean(default=True)

    # Programs that this supervisor is responsible for
    program_ids = fields.One2many(
        'student.program',
        'supervisor',
        string='Supervised Programs',
        readonly=True
    )

    # User account associated with the supervisor
    supervisor_account = fields.Many2one(
        'res.users',
        string='User Account',
        default=lambda self: self.env.user,
        required=True
    )

    # Faculty to which the supervisor belongs
    supervisor_faculty = fields.Many2one(
        'student.faculty',
        string='Faculty',
        required=True
    )

    # Compute supervisor name from user account name
    @api.depends("supervisor_account")
    def _compute_name(self):
        self.name = self.supervisor_account.name

    # Set the faculty of the user account when supervisor account is changed
    @api.onchange("supervisor_account")
    def _set_supervisor_faculty(self):
        self.supervisor_account.faculty = self.supervisor_faculty
