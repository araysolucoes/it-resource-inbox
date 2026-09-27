# -*- coding: utf-8 -*-
"""Needs: what a person asks for, in plain words, independent of the product.

Keeping the need separate from the catalog item lets requesters describe the
problem while approvers and IT decide which concrete item solves it. The need
also defines which approvals the request will require.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceNeedCategory(models.Model):
    """Simple grouping used to find needs quickly."""

    _name = 'it.resource.need.category'
    _description = 'IT need category'
    _order = 'name'

    name = fields.Char(
        string='Category',
        required=True,
        help='Groups similar needs. Example: Access, License, Equipment.',
    )
    active = fields.Boolean(string='Active', default=True)


class ItResourceNeed(models.Model):
    """Requestable need and the approvals it triggers."""

    _name = 'it.resource.need'
    _description = 'IT resource need'
    _order = 'name'

    name = fields.Char(
        string='Need',
        required=True,
        help='What the person needs, in simple words. Example: VPN access or Notebook for a new collaborator.',
    )
    code = fields.Char(
        string='Code for other modules',
        copy=False,
        help='Stable name without spaces. Other modules request the need by this code.',
    )
    category_id = fields.Many2one(
        'it.resource.need.category',
        string='Category',
        required=True,
        help='Helps to find the need. It does not choose the product.',
    )
    description = fields.Text(
        string='Description',
        help='Explain the need. The approvers are the ones who choose the item and its specification.',
    )
    approve_ti = fields.Boolean(
        string='IT approval',
        help='When checked, a configured IT user must approve before moving on.',
    )
    approve_third = fields.Boolean(
        string='Third-party approval',
        help='When checked, the approval is sent by email, through the account with SMTP and POP3, and comes back in the reply.',
    )
    approve_board = fields.Boolean(
        string='Board approval',
        help='When checked, a configured board user must approve.',
    )
    active = fields.Boolean(
        string='Status',
        default=True,
        help='Active needs can be requested. Inactive ones stay out of the lists.',
    )

    _sql_constraints = [
        (
            'it_resource_need_code_unique',
            'unique(code)',
            'A need with this code already exists.',
        ),
    ]

    def name_get(self):
        """Flag inactive needs so old requests still show why they cannot be reused."""
        result = []
        for need in self:
            label = need.name
            if not need.active:
                label = '%s (inactive)' % label
            result.append((need.id, label))
        return result

    @api.model
    def get_by_code(self, code):
        """Return the active need another module asks for by its stable code."""
        need = self.search([('code', '=', code), ('active', '=', True)], limit=1)
        if not need:
            raise UserError(_('There is no active need with code %s.') % code)
        return need
