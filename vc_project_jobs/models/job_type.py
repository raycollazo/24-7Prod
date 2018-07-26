# -*- coding: utf-8 -*-

from odoo import models, fields, api

class JobType(models.Model):

    _name = 'job.type'
    _description = 'Job Types'
    _order = 'name'

    name = fields.Char(
        string = 'Name',
        required = True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'This Job Type is already in the system! - Please check the Type and try again.')
    ]

