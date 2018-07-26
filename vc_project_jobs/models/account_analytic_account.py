# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AnalyticAccountLine(models.Model):
    _inherit = "account.analytic.line"

    rate = fields.Float(
        string = 'Rate',
    )

    job_id = fields.Many2one('project.job',
        string = 'Job',
    )


