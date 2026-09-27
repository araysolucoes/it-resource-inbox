# -*- coding: utf-8 -*-
"""Email templates used to notify approvers of a request.

Only one template per approval kind is in use at a time, which keeps the
choice of the text unambiguous when a request enters approval.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceApprovalTemplate(models.Model):
    """Email text sent to IT, board or third-party approvers."""

    _name = 'it.resource.approval.template'
    _description = 'Approval template'
    _order = 'kind, name'

    setting_id = fields.Many2one(
        'it.resource.setting',
        string='Settings',
        required=True,
        ondelete='cascade',
        index=True,
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
        help='Accepts {{{pedido}}}, {{{necessidades}}} and, for third parties, {{{aprovar}}} and {{{recusar}}}. {{pedido}} also works.',
    )
    email_to = fields.Char(
        string='Recipient email',
        help='Who receives the request when the type is Third party.',
    )
    # The default words stay in Portuguese because third parties already reply
    # with them and existing templates store them; changing the default would
    # silently change what replies are recognized for new templates.
    approve_token = fields.Char(
        string='Approval word',
        default='APROVADO',
    )
    refuse_token = fields.Char(
        string='Refusal word',
        default='RECUSADO',
    )
    in_use = fields.Boolean(
        string='In use',
        default=True,
        help='Only one template of each type is in use. The new one replaces the previous one.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create templates and switch off the previous one in use of the same kind."""
        records = super(ItResourceApprovalTemplate, self).create(vals_list)
        records._keep_single_in_use()
        return records

    def write(self, vals):
        """Save templates, keeping a single template in use per kind."""
        result = super(ItResourceApprovalTemplate, self).write(vals)
        if 'in_use' in vals or 'kind' in vals:
            self._keep_single_in_use()
        return result

    def _keep_single_in_use(self):
        # Each kind has exactly one template in use: the one just marked wins
        # and switches the others off. The context flag avoids recursion when
        # those other templates are written.
        if self.env.context.get('skip_in_use'):
            return
        for template in self.filtered('in_use'):
            others = self.search([
                ('id', '!=', template.id),
                ('setting_id', '=', template.setting_id.id),
                ('kind', '=', template.kind),
                ('in_use', '=', True),
            ])
            if others:
                others.with_context(skip_in_use=True).write({'in_use': False})

    @api.constrains('kind', 'email_to', 'body', 'approve_token', 'refuse_token')
    def _check_third(self):
        for template in self:
            if not (template.body or '').strip():
                raise UserError(_('Write the template message.'))
            if template.kind != 'third':
                continue
            if not (template.email_to or '').strip():
                raise UserError(_('Set the recipient email of the third-party template.'))
            if not (template.approve_token or '').strip() or not (template.refuse_token or '').strip():
                raise UserError(_('Set the approval word and the refusal word.'))

    def render_body(self, record, values):
        """Render the template text for a record with the given placeholder values."""
        self.ensure_one()
        return self.env['email.template']._render_text(self.body, record, values)

    def _sample_values(self):
        # Fake data so the text can be checked without opening a real request.
        self.ensure_one()
        return {
            'pedido': 'IT/TEST',
            'necessidades': 'VPN access, Headset',
            'aprovar': self.approve_token or 'APROVADO',
            'recusar': self.refuse_token or 'RECUSADO',
        }

    def action_send_test(self):
        """Send the template with sample data to the recipient or the current user."""
        self.ensure_one()
        email = (self.email_to or '').strip()
        if not email:
            email = self.env.user.email or self.env.user.partner_id.email
        if not email:
            raise UserError(_('Set the recipient email, or add an email to your user.'))
        account = self.setting_id._mail_account()
        account.send_for_record(
            False,
            0,
            email,
            _('Approval test %s') % (self.name or ''),
            self.render_body(self.env['it.resource.request'], self._sample_values()),
            body_format=self.body_format,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test sent'),
                'message': _('The template was sent to %s with the sample request IT/TEST.') % email,
                'type': 'success',
                'sticky': False,
            },
        }
