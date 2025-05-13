# This file defines the Review Table and Review Line models used in PaLMS.
# Professors review student projects by selecting from dynamically generated lines.
# It supports automated reviewer assignment, email notifications, and tracking of completion.

from odoo import models, fields, api
from markupsafe import Markup


class ReviewTable(models.Model):
    _name = 'student.review.table'
    _description = 'PaLMS - Review Tables'
    _order = 'create_date desc'

    # === BASIC INFO ===

    name = fields.Char(string='Name', required=True, default=lambda self: 'New Review Table')
    program_ids = fields.Many2many('student.program', string='Programs', required=True)
    type = fields.Selection([
        ('cw', 'Course Work (Курсовая работа)'),
        ('fqw', 'Final Qualifying Work (ВКР)')
    ], string="Project Type (КР/ВКР)", required=True)

    # Computed state based on line completeness
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='State', default='draft', tracking=True, compute='_compute_state', store=True, readonly=True, required=True)

    creator_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True, required=True)

    line_ids = fields.One2many('student.review.line', 'table_id', string='Review Lines')

    # Professors involved in this review table
    professor_ids = fields.Many2many('res.users', string='Professors', readonly=True)

    # === STATE LOGIC ===

    @api.depends('line_ids.reviewer_id', 'line_ids.sent_by', 'line_ids')
    def _compute_state(self):
        for record in self:
            if not record.line_ids:
                record.state = 'draft'
            elif all((line.reviewer_id and line.sent_by and line.sent) for line in record.line_ids):
                record.state = 'completed'
            else:
                record.state = 'in_progress'

    # === NOTIFICATION LOGIC ===

    def send_notifications_to_reviewers(self):
        for table in self:
            for line in table.line_ids:
                if line.reviewer_id and line.sent_by:
                    user = line.reviewer_id.professor_account
                    if user:
                        # Send email to reviewer
                        subtype_id = self.env.ref('student.student_message_subtype_email')
                        template = self.env.ref('student.email_template_reviewer_assigned')
                        template.send_mail(
                            line.id,
                            email_values={
                                'email_to': user.email,
                                'subtype_id': subtype_id.id
                            },
                            force_send=True
                        )

                        # Send internal Discuss message
                        message_text = Markup(
                            f"You have been assigned to review the project. See "
                            f"<a href=\"/web#id={table.id}&model=student.review.table&view_type=form\">"
                            f"{table.name}</a>."
                        )
                        self.env['student.utils'].send_message(
                            'review_line',
                            message_text,
                            [user],
                            self.env.user,
                            (str(line.project_id), str(line.project_id.name))
                        )

    # === FIELD LOGIC ===

    @api.onchange('program_ids')
    def _onchange_program_ids(self):
        # Clear lines when program changes
        self.line_ids = [(5, 0, 0)]

    # === GENERATE REVIEW LINES ===

    def action_generate_review_lines(self):
        for table in self:
            # Remove existing lines
            table.line_ids.unlink()

            # Get eligible projects with required documents
            projects = self.env['student.project'].search([
                ('project_report_file', '!=', False),
                ('plagiarism_check_file', '!=', False),
                ('student_feedback', '!=', False),
                ('program_ids', 'in', table.program_ids.ids),
                ('type', '=', table.type)
            ])

            lines = [(0, 0, {'project_id': project.id}) for project in projects]
            table.write({'line_ids': lines})

            if lines:
                # Notify professors associated with these programs
                professors = self.env['student.professor'].search([
                    ('professor_faculty.program_ids', 'in', table.program_ids.ids)
                ]).mapped('professor_account')

                # Send email
                subtype_id = self.env.ref('student.student_message_subtype_email')
                template = self.env.ref('student.email_template_review_table_created')
                template.send_mail(self.id,
                                   email_values={'email_to': ','.join(professors.mapped('email')),
                                                 'subtype_id': subtype_id.id},
                                   force_send=True)

                # Send internal Discuss message
                message_text = Markup(
                    f"A new review table <a href=\"/web#id={table.id}&model=student.review.table&view_type=form\">{table.name}</a> has been created. Please select projects for review!")
                table.env['student.utils'].send_message(
                    'review_table',
                    message_text,
                    professors,
                    table.creator_id,
                    (str(table.id), str(table.name))
                )

                table.professor_ids = [(6, 0, professors.ids)]

    # === COMPLETION CHECK ===

    def check_review_completion(self):
        for table in self:
            if table.state == 'completed':
                message_text = Markup(
                    f"All works have been sent to the reviewers for the table <a href=\"/web#id={table.id}&model=student.review.table&view_type=form\">{table.name}</a>.")
                table.env['student.utils'].send_message(
                    'review_table',
                    message_text,
                    [table.creator_id],
                    table.creator_id,
                    (str(table.id), str(table.name))
                )

    # === LIFECYCLE OVERRIDE ===

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            record.send_notifications_to_reviewers()
            record.check_review_completion()
        return result


class ReviewLine(models.Model):
    _name = 'student.review.line'
    _description = 'PaLMS - Student Review Lines'

    # Link to review table
    table_id = fields.Many2one('student.review.table', string='Review Table', required=True, ondelete='cascade')

    # Associated student project
    project_id = fields.Many2one('student.project', string='Project', required=True)

    # Assigned reviewer (professor)
    reviewer_id = fields.Many2one('student.professor', string='Reviewer')

    # Who sends the work to the reviewer (student or professor)
    sent_by = fields.Selection([
        ('student', 'Student'),
        ('professor', 'Professor')
    ], string='The work will be sent to the reviewer by')

    # Whether the work has already been sent
    sent = fields.Boolean(string='The paper has been sent to the reviewer', default=False)

    # SQL constraint to ensure a project appears only once per review table
    _sql_constraints = [
        ('unique_project_in_table', 'unique(project_id, table_id)', 'Each project can appear only once in the same review table.')
    ]
