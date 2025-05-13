# This file defines the models related to commission evaluation in PaLMS.
# Commissions are composed of professors and manage project defenses and grading.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

# Commission model: manages defense sessions and grading coordination
class Commission(models.Model):
    _name = "student.commission"
    _description = "PaLMS - Commissions"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    viewer_member = fields.Boolean(string="The viewing user is a commission member (TECHNICAL)", compute="_compute_viewer_member")
    def _compute_viewer_member(self):
        professor_account_ids = self.professor_ids.mapped('professor_account.id')
        if self.env.user.id in professor_account_ids:
            self.viewer_member = True
        else:
            self.viewer_member = False

	# Assigns the faculty of the manager creating this commission
    def _default_faculty(self):
        manager = self.env['student.manager'].sudo().search([('manager_account.id', '=', self.env.uid)], limit=1)
        if manager:
            return manager.manager_faculty
        else:
            raise ValidationError("Manager account could not be found. Please contact the system administrator.")

    lock = fields.Boolean(string="Commission is set (TECHNICAL)", default=False)

    def action_view_commission_lock(self):
        if not self.lock:
            self.lock = True

            for professor in self.professor_ids:
                professor.compute_number_of_commissions()

            for defense in self.defense_ids:
                # Set defense project commissions
                defense.project_id.commission_id = self.id
                defense.show_grades = True

                # Create grading entries
                for professor in self.professor_ids:
                    if not self.env['student.grade'].sudo().search([('project_id', '=', defense.project_id.id), ('grading_professor', '=', professor.id)]):
                        member_grade = self.env['student.grade'].sudo().create({
                            'project_id': defense.project_id.id,
                            'grading_professor': professor.id
                        }).id

                        defense.member_grades = [(4, member_grade)]

            poll_option_model = self.env['poll.option'].sudo()
            poll_model = self.env['poll.poll'].sudo()

            poll_options = poll_option_model.search([('commission_id', '=', self.id)])
            poll_ids_to_delete = poll_options.mapped('poll_id').ids

            if poll_ids_to_delete:
                polls_to_delete = poll_model.browse(poll_ids_to_delete)
                polls_to_delete.unlink()

            # Create calendar event for the commission
            self.env['student.calendar.event'].sudo().create({
                'name': f'Commission: {self.name}',
                'event_type': 'commission',
                'start_datetime': self.meeting_date,
                'end_datetime': self.meeting_date,
                'commission_id': self.id,
                'user_ids': [(6, 0, list(
                    set(self.professor_ids.mapped('professor_account.id')) |
                    set(self.defense_ids.mapped('project_student.student_account.id'))
                ))],
                'creator_id': self.env.user.id
            })

            # Log the action --------------------
            body = _('The commission №' + str(self.commission_number) + ' is set. Commission members are free to grade projects after the defense presentations.')
            self.message_post(body=body)

            # Send the email --------------------
            subtype_id = self.env.ref('student.student_message_subtype_email')
            template = self.env.ref('student.email_template_commission_set')
            template.send_mail(self.id,
                               email_values={'email_to': ','.join([professor.professor_account.email for professor in self.professor_ids]),
                                             'subtype_id': subtype_id.id},
                               force_send=True)
        else:
            self.lock = False
            for defense in self.defense_ids:
                defense.project_id.commission_id = False

            # Delete related calendar event
            event = self.env['student.calendar.event'].sudo().search([('commission_id', '=', self.id)], limit=1)
            if event:
                event.unlink()

            # Log the action --------------------
            body = _('The commission №' + str(self.commission_number) + ' is unset.')
            self.message_post(body=body)

    commission_number = fields.Integer(string='Commission Number', default=lambda self: len(self.env['student.commission'].sudo().search([]))+1, readonly=True)
    commission_faculty = fields.Many2one('student.faculty', default=_default_faculty, string='Faculty', required=True)
    name = fields.Char('Commission Name', compute="_compute_commission_name", store=True)
    defense_ids = fields.One2many('student.defense', 'commission_id', string='Defenses', required=True)
    commission_head = fields.Many2one('student.professor', string='Head of the Commission', required=True)
    professor_ids = fields.Many2many('student.professor', string='Commission Members', required=True)
    additional_files = fields.Many2many(comodel_name="ir.attachment", string="Additional Files")

    @api.onchange("additional_files")
    def _update_additional_ownership(self):
        # Makes the files public, may implement user-specific ownership in the future
        for attachment in self.additional_files:
            attachment.write({'public': True})

    @api.depends('commission_faculty')
    def _compute_commission_name(self):
        self.name = self.commission_faculty.name + " - Commission №" + str(self.commission_number)

    meeting_type = fields.Selection([('online', 'Online'), ('offline', 'Offline')], string="Meeting Type", default='online', required=True)
    meeting_location = fields.Char('Location')
    meeting_link = fields.Char('Link')
    meeting_date = fields.Datetime('Date & Time', required=True)
    meeting_other_details = fields.Text('Other Details')

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._make_attachments_public()
        return record

    def _make_attachments_public(self):
        for commission in self:
            for attachment in commission.additional_files:
                attachment.write({'public': True})

    def unlink(self):
        for record in self:
            if not record.env.user.has_group('student.group_administrator'):
                for defense in record.defense_ids:
                    for grade in defense.member_grades:
                        if grade.project_grade:
                            raise UserError(_('It is not possible to delete graded project defenses and their commissions!'))

            record.defense_ids.unlink()

        return super(Commission, self).unlink()

    @api.onchange("commission_head")
    def _update_projects_and_proposals_commission_head(self):
        for defense in self.defense_ids:
            defense.project_id.commission_head = self.commission_head
            defense.project_id.proposal_id.commission_head = self.commission_head

    def action_create_poll(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Poll - Select Options'),
            'res_model': 'poll.poll',
            'view_mode': 'form',
            'target': '_self',
        }

    @api.onchange('defense_ids')
    def _onchange_defense_ids_create_group_defenses(self):
        for commission in self:
            defenses_to_add = []
            for defense in commission.defense_ids:
                if defense.project_id.is_group_project:
                    group_projects = self.env['student.project'].search([
                        ('projects_group_id', '=', defense.project_id.projects_group_id.id),
                        ('id', '!=', defense.project_id.id)
                    ])
                    for project in group_projects:
                        if not commission.defense_ids.filtered(lambda d: d.project_id.id == project.id):
                            defenses_to_add.append((0, 0, {
                                'commission_id': commission.id,
                                'project_id': project.id,
                                'defense_time': defense.defense_time,
                            }))
            if defenses_to_add:
                commission.update({'defense_ids': commission.defense_ids.ids + defenses_to_add})

# CommissionDefense model: represents the defense of a student's project before the commission
class CommissionDefense(models.Model):
    _name = "student.defense"
    _description = "PaLMS - Commission Defenses"

    commission_id = fields.Many2one('student.commission', string='Commission', required=True)
    project_student = fields.Many2one('student.student', string='Defending Student', compute="_compute_project_student", store=True)
    project_id = fields.Many2one('student.project', string='Defense Project', required=True)
    defense_time = fields.Float(string='Defense Presentation Time', required=True)

    show_grades = fields.Boolean('Show grading section?', default=False)

    member_grades = fields.Many2many('student.grade', string='Commission Member Grades', required=True)
    final_grade = fields.Selection([('1', '1'),
                                    ('2', '2'),
                                    ('3', '3'),
                                    ('4', '4'),
                                    ('5', '5'),
                                    ('6', '6'),
                                    ('7', '7'),
                                    ('8', '8'),
                                    ('9', '9'),
                                    ('10', '10')], string='Final Commission Grade (1-10)')
    final_grade_lock = fields.Boolean(string="Final grade can be set", default=False)
    personal_grade = fields.Selection([('1', '1'),
                                       ('2', '2'),
                                       ('3', '3'),
                                       ('4', '4'),
                                       ('5', '5'),
                                       ('6', '6'),
                                       ('7', '7'),
                                       ('8', '8'),
                                       ('9', '9'),
                                       ('10', '10')], default='5', string='Your Grade (1-10)')

    def action_view_defense_grade(self):
        for grade in self.member_grades:
            if grade.grading_professor.professor_account.id == self.env.user.id:
                old_grade = grade.project_grade
                grade.project_grade = self.personal_grade

                # Check if the grading is complete when a new professor grades a defense
                self._unlock_final_grade_set()

                # Log the action --------------------
                if old_grade:
                    body = _(self.env.user.name + ' has regraded a project.')
                    self.commission_id.sudo().message_post(body=body)
                else:
                    body = _(self.env.user.name + ' has graded a project.')
                    self.commission_id.sudo().message_post(body=body)
                return
        raise ValidationError("You are not entitled to grade this project.")

    def _unlock_final_grade_set(self):
        member_grades_list = list()
        for grade in self.member_grades:
            if grade.project_grade:
                member_grades_list.append(int(grade.project_grade))
            else:
                # Abort if a professor hasn't graded the defense
                return
        self.final_grade_lock = True
        self.final_grade = str(round(sum(member_grades_list)/len(member_grades_list)))
        self._update_project_grade(True)

    @api.depends('project_id')
    def _compute_project_student(self):
        for record in self:
            if record.project_id:
                if record.project_id.student_elected:
                    record.project_student = record.project_id.student_elected
                else:
                    raise ValidationError("The chosen project is not assigned to a student.")

    @api.onchange('final_grade')
    def _update_project_grade(self, auto = False):
        if self.final_grade_lock and not auto and self.env.uid != self.commission_id.commission_head.professor_account.id:
            raise ValidationError("Only the commission head can modify the final grade.")
        else:
            self.env['student.project'].sudo().browse(self.project_id.id).grade = self.final_grade

    # RESTRICTIONS #
    _sql_constraints = [('check_uniqueness', 'UNIQUE(project_id)', 'A project defense cannot be added to multiple commissions or duplicated.')]

    def unlink(self):
        for record in self:
            if not record.env.user.has_group('student.group_administrator'):
                for grade in record.member_grades:
                    if grade.project_grade:
                        raise UserError(_('It is not possible to delete graded project defenses!'))

            record.member_grades.unlink()

        return super(CommissionDefense, self).unlink()

# CommissionGrade model: stores individual grades given by professors during defenses
class CommissionGrade(models.Model):
    _name = "student.grade"
    _description = "PaLMS - Commission Grades"

    project_id = fields.Many2one('student.project', string='Graded Project', required=True)
    grading_professor = fields.Many2one('student.professor', string='Grading Professor', required=True)
    project_grade = fields.Selection([('1', '1'),       
                                      ('2', '2'),
                                      ('3', '3'),
                                      ('4', '4'),
                                      ('5', '5'),
                                      ('6', '6'),
                                      ('7', '7'),  
                                      ('8', '8'),  
                                      ('9', '9'),  
                                      ('10', '10')], string='Member Grade (1-10)', readonly=False) 
    
    user_can_grade = fields.Boolean(string="Current user is the grading professor", compute='_compute_professor_account')

    def _compute_professor_account(self):
        for grade in self:
            grade.user_can_grade = True if grade.grading_professor.professor_account.id == self.env.user.id else False