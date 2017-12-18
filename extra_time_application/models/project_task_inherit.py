# -*- coding: utf-8 -*-
# © 2017 Elico Corp (www.elico-corp.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree


class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    sub_extra_time = fields.Float(
        'Extra Time', help='the sum of the extra time',
        default='0',
    )

    @api.multi
    def write(self, vals):
        for log in self:
            user = log.env.user
            remaining = log.remaining_hours
            if not log.env.context.get('flag') and \
                    not log.env.context.get('flag_remaine'):
                if vals.get('remaining_hours') and \
                        not vals.get('timesheet_ids'):
                    log.env['extra.time.application'].create({
                        'submit_user_id': user.id,
                        'task_id': log.id,
                        'reason': 'Automaticity create From PM or Reviewer',
                        'apply_hours':
                            vals.get('remaining_hours') - log.remaining_hours,
                        'state': 'approve',
                    })
                    log.sub_extra_time += \
                        (vals.get('remaining_hours') - log.remaining_hours)
                for record in vals.get('timesheet_ids', []):
                    if record[0] == 0:
                        remaining -= record[2]['unit_amount']
                    elif record[0] == 2:
                        item = log.timesheet_ids.search([
                            ('id', '=', record[1])
                        ])
                        remaining += item['unit_amount']
                if remaining < 0:
                    raise UserError(
                        _(
                            'The task have no enough time, '
                            'please Apply for more extra time'
                        ))
        res = super(ProjectTaskInherit, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        user = self.env.user
        is_exist = user.has_group(
            'extra_time_application.group_project_task_manager')
        if not vals.get('project_id.is_modified'):
            if not is_exist and self.project_id.user_id != user:
                raise UserError(
                    _('You do not have permission'))
        return super(ProjectTaskInherit, self).create(vals)

    @api.multi
    def open_extra_time_line(self):
        for record in self:
            domain = [('task_id', '=', record.name)]
            return {
                'name': _('Extra Time Approve'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'extra.time.application',
                'target': 'current',
                'domain': domain,
            }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        res = super(ProjectTaskInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        dom = etree.XML(res['arch'])
        if view_type == 'form':
            user = self.env.user
            is_exist = user.has_group(
                'extra_time_application.group_project_task_manager')
            if is_exist or self.project_id.is_modified:
                for node in dom.xpath("//field[@name='remaining_hours']"):
                    node.set("modifiers", '{"readonly": false}')
            res['arch'] = etree.tostring(dom)
        return res
