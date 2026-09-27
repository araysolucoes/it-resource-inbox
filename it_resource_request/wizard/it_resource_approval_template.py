# -*- coding: utf-8 -*-
"""Wizard that creates an approval template.

The settings list is read-only for creation, so new templates always go
through this wizard, which validates third-party fields before saving.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceApprovalTemplateWizard(models.TransientModel):
    """Form used to create a new approval template."""

    _name = 'it.resource.approval.template.wizard'
    _description = 'New approval template'

    setting_id = fields.Many2one(
        'it.resource.setting',
        string='Settings',
        required=True,
        default=lambda self: self.env['it.resource.setting'].get_setting(),
    )
    name = fields.Char(string='Name', required=True)
    kind = fields.Selection(
        [
            ('ti', 'IT'),
            ('board', 'Board'),
            ('third', 'Third party'),
        ],
        string='Type',
        required=True,
        default='third',
    )
    body_format = fields.Selection(
        [('text', 'Text'), ('html', 'HTML')],
        string='Content type',
        default='text',
        required=True,
    )
    body = fields.Text(
        string='Message',
        required=True,
        help='{{{pedido}}}, {{{necessidades}}}, {{{aprovar}}} and {{{recusar}}}. {{pedido}} also works.',
    )
    email_to = fields.Char(string='Recipient email')
    approve_token = fields.Char(string='Approval word', default='APROVADO')
    refuse_token = fields.Char(string='Refusal word', default='RECUSADO')
    in_use = fields.Boolean(string='In use', default=True)

    @api.onchange('kind')
    def _onchange_kind(self):
        # Only third-party templates are emailed to a fixed address; internal
        # ones go to the group members, so a leftover address is cleared.
        if self.kind != 'third':
            self.email_to = False

    def action_create(self):
        """Validate the input and create the approval template."""
        self.ensure_one()
        if not (self.body or '').strip():
            raise UserError(_('Write the template message.'))
        if self.kind == 'third':
            if not (self.email_to or '').strip():
                raise UserError(_('Set the recipient email.'))
            if not (self.approve_token or '').strip() or not (self.refuse_token or '').strip():
                raise UserError(_('Set the approval word and the refusal word.'))
        self.env['it.resource.approval.template'].create({
            'setting_id': self.setting_id.id,
            'name': self.name,
            'kind': self.kind,
            'body_format': self.body_format,
            'body': self.body,
            'email_to': self.email_to if self.kind == 'third' else False,
            'approve_token': self.approve_token if self.kind == 'third' else False,
            'refuse_token': self.refuse_token if self.kind == 'third' else False,
            'in_use': self.in_use,
        })
        return {'type': 'ir.actions.act_window_close'}
