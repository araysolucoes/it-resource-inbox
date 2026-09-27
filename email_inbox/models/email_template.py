# -*- coding: utf-8 -*-
"""Reusable email templates with safe placeholder substitution.

Templates are looked up by a stable ``code`` so other modules can send them
without depending on database ids. Placeholders are replaced by plain string
substitution (never by evaluating code): ``{{{name}}}`` and ``{{name}}`` take
values passed by the caller, and ``{{object.field}}`` reads simple fields of
the linked record.
"""
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Triple braces are replaced first: if the double-brace pattern ran first on
# "{{{name}}}", it would consume the inner "{{name}}" and leave a stray "{" and
# "}" around the value.
_TRIPLE = re.compile(r'\{\{\{\s*([^{}]+)\s*\}\}\}')
_DOUBLE = re.compile(r'\{\{\s*([^{}]+)\s*\}\}')
_SIMPLE_TYPES = (
    'char', 'text', 'integer', 'float', 'monetary',
    'selection', 'boolean', 'date', 'datetime',
)


class EmailTemplate(models.Model):
    _name = 'email.template'
    _description = 'Email Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help='Name used to find the template in the list. Example: Order notice.',
    )
    code = fields.Char(
        string='Code for Other Modules',
        required=True,
        copy=False,
        help='Stable name without spaces. The other module sends by this code. Example: order_notice.',
    )
    account_id = fields.Many2one(
        'email.account',
        string='Sending Account',
        domain=[('active', '=', True)],
        help='Account that sends this template. Empty uses the default account.',
    )
    email_to = fields.Char(
        string='Suggested Recipient',
        help='Can be left empty. Accepts fixed text, {{object.email}} or {{{object.email}}}.',
    )
    subject = fields.Char(
        string='Subject',
        help='Accepts {{object.field}}, {{key}} and, in HTML, {{{variable}}}.',
    )
    body_format = fields.Selection(
        [('text', 'Text'), ('html', 'HTML')],
        string='Content Type',
        default='text',
        required=True,
        help='In HTML, {{{variable}}} receives the value sent by the other module.',
    )
    body = fields.Text(
        string='Body',
        help='Plain text letter, or HTML with {{{variable}}}.',
    )
    variable_ids = fields.One2many(
        'email.template.variable',
        'template_id',
        string='Variables',
        help='Names filled in by another module. In HTML they are written as {{{name}}}.',
    )
    preview_html = fields.Html(
        string='Preview',
        compute='_compute_preview_html',
        sanitize=False,
    )
    active = fields.Boolean(string='Template in Use', default=True)

    _sql_constraints = [
        (
            'email_template_code_unique',
            'unique(code)',
            'A template with this code already exists.',
        ),
    ]

    def _render_text(self, text, record, values):
        """Replace {{{variable}}} and {{key}} without executing any code."""
        values = values or {}
        record = record if record else self.env['email.template']

        def replace(match):
            key = (match.group(1) or '').strip()
            if key in values and values[key] is not False:
                return str(values[key])
            if key.startswith('object.') and record and len(record) == 1:
                fname = key.split('.', 1)[1]
                field = record._fields.get(fname)
                if field and field.type in _SIMPLE_TYPES:
                    value = record[fname]
                    if value is False or value is None:
                        return ''
                    if field.type == 'selection':
                        selection = field.selection(record) if callable(field.selection) else field.selection
                        return dict(selection or []).get(value, str(value))
                    return str(value)
            return ''

        rendered = _TRIPLE.sub(replace, text or '')
        return _DOUBLE.sub(replace, rendered)

    @api.depends('body', 'body_format', 'subject', 'account_id', 'variable_ids', 'variable_ids.name', 'variable_ids.description')
    def _compute_preview_html(self):
        for template in self:
            values = {}
            for variable in template.variable_ids:
                values[variable.name] = variable.description or variable.name
            rendered = template._render_text(template.body, template.browse(), values)
            template.preview_html = template.account_id._message_preview_html(
                rendered, template.body_format or 'text',
            )

    def _render_for(self, res_model, res_id, email_to=None, values=None):
        self.ensure_one()
        if res_model and res_id:
            record = self.env[res_model].browse(res_id).exists()
        else:
            record = self.browse()
        recipient = email_to or self._render_text(self.email_to, record, values)
        if not recipient:
            raise UserError(_('Please provide the recipient for template %s.') % self.name)
        return {
            'email_to': recipient,
            'subject': self._render_text(self.subject, record, values),
            'body': self._render_text(self.body, record, values),
        }

    def send_for(self, res_model, res_id, email_to=None, values=None, email_cc=False, attachment_ids=None):
        """Send this template linked to a record of another module."""
        self.ensure_one()
        if not self.active:
            raise UserError(_('Template %s is inactive.') % self.name)
        account = self.account_id or self.env['email.account'].get_default_account()
        rendered = self._render_for(res_model, res_id, email_to=email_to, values=values)
        message = account.send_for_record(
            res_model,
            res_id,
            rendered['email_to'],
            rendered['subject'],
            rendered['body'],
            email_cc=email_cc,
            attachment_ids=attachment_ids,
            body_format=self.body_format,
        )
        if message:
            message.sudo().write({'template_id': self.id})
        return message

    @api.model
    def send(self, code, res_model, res_id, email_to=None, values=None, email_cc=False, attachment_ids=None):
        """Entry point for other modules: send by template code."""
        template = self.search([('code', '=', code), ('active', '=', True)], limit=1)
        if not template:
            raise UserError(_('There is no active email template with code %s.') % code)
        return template.send_for(
            res_model,
            res_id,
            email_to=email_to,
            values=values,
            email_cc=email_cc,
            attachment_ids=attachment_ids,
        )


class EmailTemplateVariable(models.Model):
    _name = 'email.template.variable'
    _description = 'Email Template Variable'
    _order = 'name'

    template_id = fields.Many2one(
        'email.template',
        string='Template',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(
        string='Name',
        required=True,
        help='Written in HTML as {{{name}}}. No spaces and no braces.',
    )
    description = fields.Char(
        string='What to Fill In',
        help='Reminder of the data the other module will send. The preview shows this text.',
    )

    @api.constrains('name')
    def _check_name(self):
        for variable in self:
            name = (variable.name or '').strip()
            if not name or re.search(r'[\s{}]', name):
                raise UserError(_('The variable name cannot contain spaces or braces.'))
