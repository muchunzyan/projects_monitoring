# This model represents student applications to published or applied projects.
# It handles validation, state transitions (draft → sent → accepted/rejected),
# communication with professors, access control, and categorization logic.

from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from dateutil.relativedelta import relativedelta

class Application(models.Model):
	_name = 'student.application'
	_description = 'PaLMS - Applications for Projects'
	_rec_name = 'applicant'
	_inherit = ['mail.thread', 'student.utils']

	# Compute and populate student-related details from the applicant record
	@api.depends('applicant')
	def _compute_student_details(self):
		for applicant in self.applicant:
			self.email = applicant.student_email
			self.phone = applicant.student_phone
			self.student_program = applicant.student_program.name
			self.student_degree = applicant.progress
			self.student_id = applicant.student_id

	# Default method to assign the current user's linked student account as the applicant
	def _default_applicant(self):
		student = self.env['student.student'].sudo().search([('student_account.id', '=', self.env.uid)], limit=1)
		self._compute_student_details()
		if student:
			return student.id
		else:
			raise ValidationError("Student account could not be found. Please contact the supervisor.")

	# The student submitting the application
	applicant = fields.Many2one('student.student', string='Applicant', default=_default_applicant, readonly=True, required=True)
	# The res.users account linked to the applicant student
	applicant_account = fields.Many2one('res.users', string="Applicant Account", compute='_compute_applicant_account', store=True)

	# Student's primary email, computed from applicant
	email = fields.Char('Email', compute="_compute_student_details", store=True, readonly=True)
	# Optional additional email provided by the applicant
	additional_email = fields.Char('Additional Email', required=False)
	# Student's primary phone, computed from applicant
	phone = fields.Char('Phone', compute="_compute_student_details", store=True, readonly=True)
	# Optional additional phone number provided by the applicant
	additional_phone = fields.Char('Additional Phone', required=False)
	# Optional Telegram ID for communication
	telegram = fields.Char('Telegram ID', required=False)
	# Student's program/track, computed from applicant
	student_program = fields.Char("Student Track", compute="_compute_student_details", store=True, readonly=True)
	# Student's academic year or degree progress, computed from applicant
	student_degree = fields.Char("Academic Year", compute="_compute_student_details", store=True, readonly=True)
	# Student's unique ID, computed from applicant
	student_id = fields.Char("Student ID", compute="_compute_student_details", store=True, readonly=True)

	# The message content of the application, required for submission
	message = fields.Text('Application Message', required=True)
	# Feedback provided by the professor upon review
	feedback = fields.Text('Professor Feedback')
	# Additional files attached to the application (e.g., documents, CV)
	additional_files = fields.Many2many(comodel_name="ir.attachment", string="Additional Files")

	# Current state of the application in the workflow
	state = fields.Selection([('draft', 'Draft'),('sent', 'Sent'),('accepted', 'Accepted'),('rejected', 'Rejected')], default='draft', readonly=True, string='Application State', store=True)
	# Date when the application was sent to the professor
	sent_date = fields.Date(string='Sent Date')

	# Computed field to categorize applications into urgency groups based on sent_date and state
	urgency_category = fields.Selection([
        ('pending', 'Pending'),
        ('urgent', 'Urgent'),
        ('missed', 'Missed'),
		('handled', 'Handled')
    ], string='Urgency', compute='_compute_urgency_category', store=True)

	# Compute urgency category based on application state and date sent
	def _compute_urgency_category(self):
		today = fields.Date.today()
		for record in self:
			if record.state == 'accepted' or record.state == 'rejected':
				record.urgency_category = 'handled'
			elif (record.sent_date + relativedelta(days=3)) > today:
				record.urgency_category = 'pending'
			elif (record.sent_date + relativedelta(days=3)) == today:
				record.urgency_category = 'urgent'
			else:
				record.urgency_category = 'missed'

	# The project to which this application is submitted; must be published or applied state
	project_id = fields.Many2one('student.project', string='Project', required=True, domain=[('state_publication','in',['published','applied'])])

	# Compute the applicant's user account from the applicant student record
	@api.depends('applicant')
	def _compute_applicant_account(self):
		for application in self:
			application.applicant_account = application.applicant.student_account

	# Ensure a student can only apply once per project
	_sql_constraints = [
        ('check_uniqueness', 'UNIQUE(applicant, project_id)', 'You have already applied to this project.')
	]

	# Color coding for UI boxes representing application states
	color = fields.Integer(string="Box Color", default=4, compute='_compute_color_value', store=True)

	# Compute the color value based on the state of the application
	@api.depends('state')
	def _compute_color_value(self):
		if self.state == 'draft':
			self.color = 4
		elif self.state == 'sent':
			self.color = 3
		elif self.state == 'accepted':
			self.color = 10
		elif self.state == 'rejected':
			self.color = 9

	# The professor responsible for the applied project; defaulted from project
	application_professor = fields.Many2one('res.users', string='Professor of the Applied Project', default=lambda self: self.project_id.professor_account)

	# Constraint to prevent students from editing feedback except in draft state
	@api.constrains('feedback')
	def _feedback_control(self):
		if self.env.user.has_group('student.group_student') and self.state != 'draft':
			raise AccessError("You don't have permission to edit the feedback. Please use the log or send a message to the project creator.")

	# Update the application_professor field when project changes
	@api.depends('project_id')
	def _check_professor(self):
		self.application_professor = self.project_id.professor_account

	# Validation to ensure feedback is provided and sufficiently detailed on rejection
	def _check_feedback(self):
		if not self.feedback:
			raise UserError("You have to provide a reason for rejection.")
		if len(self.feedback) < 20:
			raise UserError("Please provide a more detailed feedback (at least 20 characters).")

	# Override create to disable default tracking and customize creation message
	@api.model
	def create(self, vals):
		application = super(Application, self.with_context(tracking_disable=True)).create(vals)

		application._make_attachments_public()

		# Log a customized message on creation
		message = _("A new application has been created by %s.") % (self.env.user.name)
		application.message_post(body=message)

		return application

	# Make all attachments public so other users can access them
	def _make_attachments_public(self):
		for application in self:
			for attachment in application.additional_files:
				attachment.write({'public': True})

	# Check that the current user is authorized to modify the application
	@api.onchange('email', 'message', 'project_id', 'additional_email', 'additional_phone', 'telegram')
	def _check_user_identity(self):
		if not self.env.user.has_group('student.group_supervisor'):
			if self.applicant_account != self.env.user:
				raise AccessError("You can only modify applications that you created. If you require assistance, contact the supervisor.")

	# Action to send the application to the professor for evaluation
	@api.depends('project_id.state_publication')
	def action_view_application_send(self):
		self._check_user_identity()

		# Prevent resending if already sent
		if self.state != 'draft':
			raise UserError("The application is already sent!")
		# Ensure project is open for applications
		elif self.project_id.state_publication not in ['published', 'applied']:
			raise UserError("The chosen project is not available for applications, please try another one.")
		# Check if user already has a sent application
		elif self.env['student.application'].search([
				('applicant_account', '=', self.env.user.id),
				('state', '=', "sent")
			]):
			raise UserError("You have already sent an application for a project. Please wait up to 3 days to receive a response or cancel the application.")
		else:
			# Change state to sent and update professor field
			self.write({'state': 'sent'})
			self.application_professor = self.project_id.professor_account

			# Update ownership of attached files so others can access them
			for attachment in self.additional_files:
				attachment.write({'res_model': self._name, 'res_id': self.id})

			# Log the sending action in chatter
			body = _('The application is sent to the professor, %s, for evaluation.', self.project_id.professor_account.name)
			self.message_post(body=body)

			body = _('An application is sent by %s.', self.applicant_account.name)
			self.project_id.message_post(body=body)

			# Send notification email to professor
			subtype_id = self.env.ref('student.student_message_subtype_email')
			template = self.env.ref('student.email_template_application_send')
			template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)
			# -----------------------------------

			# Construct and send a chat message notifying the professor
			message_text = f'<strong>Application Received</strong><p> ' + self.applicant_account.name + " sent an application for " + self.project_id.name + ". Please evaluate the application.</p>"

			self.env['student.utils'].send_message('application', Markup(message_text), self.application_professor, self.applicant_account, (str(self.id),str(self.project_id.name)))

			# Record the date sent
			self.sent_date = fields.Date.today()

			return self.env['student.utils'].message_display('Sent', 'The application is submitted for review.', False)

	# Action to cancel a sent application and revert to draft state
	def action_view_application_cancel(self):
		self._check_user_identity()

		if self.state == 'sent':
			self.write({'state': 'draft'})

			# Log cancellation in chatter
			body = _('The application submission is cancelled.')
			self.message_post(body=body)
			self.project_id.message_post(body=body)

			return self.env['student.utils'].message_display('Cancellation', 'The application submission is cancelled.', False)
		else:
			raise UserError("The application is already processed!")

	# Automatically reject other applications to the same project when one is accepted
	@api.model
	def mark_other_applications(self):
		if self.project_id and self.state == 'accepted':
			other_apps = self.env['student.application'].search([
				('project_id', '=', self.project_id.id),
				('id', '!=', self.id),
			])
			for app in other_apps:
				app.action_view_application_auto_reject()

	# Security check to ensure only the professor of the project can respond to applications
	def _check_professor_identity(self):
		if not self.env.user.has_group('student.group_supervisor'):
			if self.project_id.professor_account != self.env.user:
				raise AccessError("You can only respond to the applications sent to your projects.")

	# Action to accept an application, assign project and notify involved parties
	def action_view_application_accept(self):
		self._check_professor_identity()

		if self.state == 'sent':
			self.write({'state': 'accepted'})

			# Update project state and assign the student
			self.project_id.sudo().write({
				'state_publication': 'assigned', 'assigned': True,
				'project_state': 'assigned',
				'student_elected': [(4, self.applicant.id)]
			})
			self.project_id.sudo().create_project_project()

			# Add the user to the elected student group for access rights
			group_id = self.env.ref('student.group_elected_student')
			group_id.users = [(4, self.applicant_account.id)]

			# Log acceptance in chatter
			body = _('This application is accepted by the professor.')
			self.message_post(body=body)

			body = _('The application sent by %s is accepted.', self.applicant_account.name)
			self.project_id.message_post(body=body)

			# Send email notification of acceptance
			subtype_id = self.env.ref('student.student_message_subtype_email')
			template = self.env.ref('student.email_template_application_accept')
			template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)
			# -----------------------------------

			# Construct and send chat message notifying applicant of acceptance
			message_text = f'<strong>Application Accepted</strong><p> This application submitted for «' + self.project_id.name + '» is accepted by the professor. You can contact the project professor to start working on it.</p>'

			self.env['student.utils'].send_message('application', Markup(message_text), self.applicant_account, self.application_professor, (str(self.id),str(self.project_id.name)))

			# Automatically reject other applications for this project
			self.mark_other_applications()

			return self.env['student.utils'].message_display('Accepted', 'The selected application is chosen for the project, remaining ones are automatically rejected.', False)
		else:
			raise UserError("The application is already processed or still a draft!")

	# Action to reject an application with required feedback and notifications
	def action_view_application_reject(self):
		self._check_professor_identity()

		if self.state == 'sent':
			self._check_feedback()

			self.write({'state': 'rejected'})

			# Log rejection in chatter
			body = _('This application is rejected by the professor.')
			self.message_post(body=body)

			body = _('The application sent by %s is rejected.', self.applicant_account.name)
			self.project_id.message_post(body=body)

			# Send email notification of rejection
			subtype_id = self.env.ref('student.student_message_subtype_email')
			template = self.env.ref('student.email_template_application_reject')
			template.send_mail(self.id, email_values={'subtype_id': subtype_id.id}, force_send=True)
			# -----------------------------------

			# Construct and send chat message notifying applicant of rejection with feedback
			message_text = f'<strong>Application Rejected</strong><p> This application submitted for <i>' + self.project_id.name + '</i> is rejected by the professor. Please check the <b>Feedback</b> section to learn about the reason.</p>'

			self.env['student.utils'].send_message('application', Markup(message_text), self.applicant_account, self.application_professor, (str(self.id),str(self.project_id.name)))

			return self.env['student.utils'].message_display('Rejection', 'The application is rejected.', False)
		else:
			raise UserError("The application is already processed or still a draft!")

	# Automatically reject an application when another is accepted for the same project
	def action_view_application_auto_reject(self):
		if self.state == 'sent':
			self.write({'state': 'rejected'})

			# Log automatic rejection in chatter
			body = _('This application is rejected as another one is accepted by the professor.')
			self.message_post(body=body)

			# Use Odoo Bot as sender for the notification message
			odoobot = self.env.ref('base.user_root')

			# Construct and send chat message notifying applicant of automatic rejection
			message_text = f'<strong>Application Rejected</strong><p> This application submitted for <i>' + self.project_id.name + '</i> is automatically rejected since another one is chosen by the professor.</p>'

			self.env['student.utils'].send_message('application', Markup(message_text), self.applicant_account, odoobot, (str(self.id),str(self.project_id.name)))

	# Field indicating if chat messages should be invisible to the current user
	chat_invisible = fields.Boolean("Chat Invisible", compute="_compute_chat_invisible", store=False)

	# Compute chat visibility based on user roles and relation to the application
	def _compute_chat_invisible(self):
		accepted_ids = [
			self.application_professor.id,
			self.applicant.student_account.id
		]

		for project in self:
			user = self.env.user
			# Chat is visible only to the professor, the applicant, or administrators
			project.chat_invisible = not (
					(user.id in accepted_ids) or
					self.env.user.has_group('student.group_administrator'))
