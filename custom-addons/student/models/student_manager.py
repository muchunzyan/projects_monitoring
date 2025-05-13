# This model defines academic managers in the PaLMS system.
# Managers are responsible for overseeing academic programs within a specific faculty.

from odoo import api, fields, models

class Manager(models.Model):
    _name = "student.manager"
    _description = "PaLMS - Managers"

    # Display name of the manager (computed from user account)
    name = fields.Char('Manager Name', required=True, default=lambda self: self.env.user.name, compute="_compute_name", store=True, readonly=True)

    # Whether the manager is currently active
    active = fields.Boolean(default=True)

    # Programs managed by this manager
    program_ids = fields.One2many('student.program', 'manager', string='Managed Programs', readonly=True)

    # Related user account
    manager_account = fields.Many2one('res.users', string='User Account', default=lambda self: self.env.user, required=True)

    # Faculty to which the manager belongs
    manager_faculty = fields.Many2one('student.faculty', string='Faculty', required=True)

    # Compute the name of the manager based on the linked user account
    @api.depends("manager_account")
    def _compute_name(self):
        self.name = self.manager_account.name

    # Ensure that changing the manager account also updates the faculty (if relevant logic is defined)
    @api.onchange("manager_account")
    def _set_manager_faculty(self):
        self.manager_account.faculty = self.manager_faculty