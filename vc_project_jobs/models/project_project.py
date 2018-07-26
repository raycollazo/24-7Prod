# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError

import logging
_logger = logging.getLogger(__name__)

class Project(models.Model):

    _inherit = 'project.project'

    # for top level projects
    job_project_ids = fields.One2many('project.job', 'project_id', string='Jobs', domain=[('active', '=', True)])

    job_count = fields.Integer(compute='_get_job_count', string="Jobs")

    supports_jobs = fields.Boolean(string="Allow Jobs")

    @api.depends('job_project_ids')
    def _get_job_count(self):
        for project in self:
            project.job_count = len(project.job_project_ids.ids)

class ProjectJobs(models.Model):

    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Job"
    _name = 'project.job'
    _order = "priority desc, sequence, id desc"

    name = fields.Char(string="Job Name")

    type = fields.Many2one('job.type',
        string = 'Type',
    )

    stage_id = fields.Selection(
        [('0', 'Planning'),
         ('1', 'Ready to Start'),
         ('2', 'In Progress'),
         ('3', 'Close Out'),
         ('4', 'Billing'),
         ('5', 'Complete'),
        ], string='State',
        group_expand='_expand_states',
        default='0')

    def _expand_states(self, states, domain, order):
        # return all possible states, in order
        return [key for key, val in type(self).stage_id.selection]

    color = fields.Integer(string='Color Index')

    partner_id = fields.Many2one(
        string = 'Customer',
        comodel_name = 'res.partner',
        related = 'project_id.partner_id',
    )

    active = fields.Boolean(default=True,
        help="If the active field is set to False, it will allow you to hide the project without removing it.")

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of Jobs.")

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ], default='0', index=True, string="Priority")

    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True,
        help="A task's kanban state indicates special situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the progress of this job\n"
             " * Green indicates the job is ready to be pulled to the next stage")

    project_id = fields.Many2one('project.project', string='Project', index=True, required=True)

    daily_report_ids = fields.One2many('job.daily.report','job_id', string='Daily Reports')

    user_id = fields.Many2one('res.users',
                              string='Project Manager',
                              default=lambda self: self.env.user,
                              track_visibility="onchange")

    date_from = fields.Date('Scheduled Start')

    date_to = fields.Date('Scheduled Finish')

    hotel_name = fields.Many2one(
        string = 'Hotel Name',
        comodel_name = 'res.partner',
        domain = [('supplier','=',True)]
    )

    foreman_id = fields.Many2one(
        string = 'Foreman',
        comodel_name = 'hr.employee',
    )

    crew_id = fields.Many2one(
        comodel_name = 'job.crew',
        string = 'Job Crew',
    )

    crew_employees = fields.Many2many(
        comodel_name = 'hr.employee',
        string = 'Crew Members',
        related = 'crew_id.employee_ids',
    )

    job_instructions = fields.Text(
        string = 'Instructions',
    )

    site_id = fields.Many2one(
        comodel_name = 'res.partner',
        string = 'Site',
        domain = "[('type','=','job')]"
    )

    daily_report_count = fields.Integer(compute='_get_daily_report_count', string="Daily Reports")

    @api.depends('daily_report_ids')
    def _get_daily_report_count(self):
        for job in self:
            job.daily_report_count = len(job.daily_report_ids.ids)

    planned_hours = fields.Float(string='Initially Planned Hours',
       help='Estimated time to do the job, usually set by the project manager.')

    remaining_hours = fields.Float(string='Remaining Hours', digits=(16,2),
       help="Total remaining time, can be re-estimated periodically by the assignee of the job.")


    @api.depends('stage_id', 'timesheet_ids.unit_amount', 'planned_hours')
    def _hours_get(self):
        for task in self.sorted(key='id', reverse=True):
            task.effective_hours = sum(task.sudo().timesheet_ids.mapped('unit_amount'))
            task.remaining_hours = task.planned_hours - task.effective_hours
            task.total_hours = max(task.planned_hours, task.effective_hours)
            task.total_hours_spent = task.effective_hours
            task.delay_hours = max(-task.remaining_hours, 0.0)

            if task.stage_id == 5:
                task.progress = 100.0
            elif (task.planned_hours > 0.0):
                task.progress = round(100.0 * (task.effective_hours) / task.planned_hours, 2)
            else:
                task.progress = 0.0

    remaining_hours = fields.Float(compute='_hours_get', store=True, string='Remaining Hours',
                                   help="Total remaining time, can be re-estimated periodically by the assignee of the job.")
    effective_hours = fields.Float(compute='_hours_get', store=True, string='Hours Spent',
                                   help="Computed using the sum of the job work done.")
    total_hours = fields.Float(compute='_hours_get', store=True, string='Total', help="Computed as: Time Spent + Remaining Time.")
    total_hours_spent = fields.Float(compute='_hours_get', store=True, string='Total Hours', help="Computed as: Time Spent + Sub-job Hours.")
    progress = fields.Float(compute='_hours_get', store=True, string='Progress', group_operator="avg")
    delay_hours = fields.Float(compute='_hours_get', store=True, string='Delay Hours',
                               help="Computed as difference between planned hours by the project manager and the total hours of the job.")
    children_hours = fields.Float(compute='_hours_get', store=True, string='Sub-job Hours')
    timesheet_ids = fields.One2many('account.analytic.line', 'task_id', 'Timesheets')

    _constraints = [(models.BaseModel._check_recursion, 'Circular references are not permitted between tasks and sub-tasks', ['parent_id'])]


