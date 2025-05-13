# This model stores student-submitted results for milestones.
# Each result may include attachments, comments, and is linked to a student project and milestone.
# Access and visibility are restricted based on user roles.

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.osv import expression

class MilestoneResult(models.Model):
    _name = 'student.milestone.result'
    _description = 'PaLMS - Milestones Results'

    # Related milestone for which the result is submitted.
    milestone_id = fields.Many2one(
        'student.milestone',
        string='Milestone',
        required=True,
        ondelete='cascade'
    )
    # User who submitted the result.
    user_id = fields.Many2one(
        'res.users',
        string='Submitted By',
        required=True,
        default=lambda self: self.env.user
    )
    # Related student project for which this result is submitted.
    student_project_id = fields.Many2one(
        'student.project',
        string='Project'
    )
    # File attachments for the result.
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='milestone_result_attachment_rel',
        column1='milestone_id',
        column2='attachment_id',
        string='Attachments'
    )
    # Optional comment submitted with the result.
    comment = fields.Text(string='Comment')
    # Date and time of submission (set automatically).
    submit_date = fields.Datetime(
        string='Submitted On',
        default=fields.Datetime.now,
        readonly=True,
        required=True
    )
    # Field used in views to toggle readonly access to base fields.
    base_fields_readonly = fields.Boolean(
        string='Base fields readonly',
        # compute='_compute_can_edit_base_fields',
        store=False
    )

    # SQL constraint to enforce one result per user/project/milestone combination.
    _sql_constraints = [
        (
            'unique_result_per_user',
            'unique(milestone_id, student_project_id, user_id)',
            'You can only submit one result from project per milestone.'
        )
    ]

    @api.model
    def create(self, vals):
        # Ensure milestone_id is provided
        milestone_id = vals.get('milestone_id') or self.env.context.get('default_milestone_id')
        if isinstance(milestone_id, (list, tuple)):
            milestone_id = milestone_id[0] if milestone_id else False
        if not milestone_id:
            raise ValidationError("Milestone ID is missing.")
        # Create record and set attachment visibility
        record = super().create(vals)
        record._make_attachments_public()
        return record

    def write(self, vals):
        # Update attachment visibility on write
        self._make_attachments_public()
        return super().write(vals)

    def _make_attachments_public(self):
        # Ensure all attached files are public
        for milestone in self:
            for attachment in milestone.attachment_ids:
                attachment.write({'public': True})

    def _search(self, domain, offset=0, limit=None, order=None):
        # Apply role-based visibility filtering
        user = self.sudo().env.user
        if not (
                user.has_group('student.group_manager') or
                user.has_group('student.group_supervisor') or
                user.has_group('student.group_administrator') or
                user.has_group('base.group_system')
        ):
            # Limit to projects where the user is a student or professor
            projects = self.env['student.project'].search([])
            permitted_user_ids = projects.mapped('student_account.id') + projects.mapped('professor_account.id')
            domain = expression.AND([domain, [('user_id', 'in', permitted_user_ids)]])
        return super()._search(domain, offset=offset, limit=limit, order=order)
