# -*- coding: utf-8 -*-
"""Single settings record of the approval flow and the demo data loader.

The settings hold the approval templates and decide which email account is
used. The demo loader is idempotent: it can be clicked several times and only
adds what is missing, including records created by older (Portuguese) versions
of the module.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceSetting(models.Model):
    """Container of the approval templates; only one record is expected."""

    _name = 'it.resource.setting'
    _description = 'IT approval settings'

    name = fields.Char(default='Approvals', required=True)
    template_ids = fields.One2many(
        'it.resource.approval.template',
        'setting_id',
        string='Approval templates',
    )

    @api.model
    def get_setting(self):
        """Return the settings record, creating it on first use."""
        setting = self.search([], limit=1)
        if not setting:
            setting = self.sudo().create({'name': 'Approvals'})
        return setting

    def action_open(self):
        """Open the settings form with the approval templates."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval templates'),
            'res_model': 'it.resource.setting',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_new_template(self):
        """Open the wizard that creates a new approval template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New template'),
            'res_model': 'it.resource.approval.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_setting_id': self.id},
        }

    def _template_in_use(self, kind):
        self.ensure_one()
        return self.env['it.resource.approval.template'].search([
            ('setting_id', '=', self.id),
            ('kind', '=', kind),
            ('in_use', '=', True),
        ], limit=1)

    def _mail_account(self, required=True):
        # The approval screen does not let users pick a server. The default
        # account of the Email inbox is used, and it needs both SMTP (to send)
        # and POP (to read third-party replies).
        account = self.env['email.account'].search([
            ('active', '=', True),
            ('is_default', '=', True),
            ('smtp_enabled', '=', True),
            ('pop_enabled', '=', True),
        ], limit=1)
        if not account and required:
            raise UserError(_(
                'Mark an account as default in the Email inbox and enable SMTP and POP.'
            ))
        return account

    def _check_third_ready(self):
        self.ensure_one()
        template = self._template_in_use('third')
        if not template or not (template.email_to or '').strip():
            raise UserError(_(
                'In Settings, keep a third-party template in use, with the recipient email.'
            ))
        self._mail_account()
        return template

    @api.model
    def action_load_demo(self):
        """Load the demo catalog and, when email is configured, the demo templates.

        No form is opened: the result is reported in a notification. Email
        templates are skipped without a mail server so the demo never leaves
        templates that cannot be sent.
        """
        setting = self.get_setting()
        added = setting._load_demo_catalog()
        mail_ready = setting._demo_mail_ready()
        if mail_ready:
            if setting._load_demo_mail():
                added.append(_('email templates'))
        if added and not mail_ready:
            message = _(
                'Added %s. The email demo was left out: '
                'configure an outgoing mail server or an account in the Email inbox.'
            ) % ', '.join(added)
            kind = 'warning'
            sticky = True
        elif added:
            message = _('Demo data added: %s.') % ', '.join(added)
            kind = 'success'
            sticky = False
        elif not mail_ready:
            message = _(
                'The demo data was already loaded. '
                'The email demo stays out until there is an outgoing server or an account in the Email inbox.'
            )
            kind = 'warning'
            sticky = True
        else:
            message = _('The demo data was already loaded.')
            kind = 'warning'
            sticky = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Demo'),
                'message': message,
                'type': kind,
                'sticky': sticky,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _demo_mail_ready(self):
        # Either an Odoo outgoing mail server or an account already registered
        # in the Email inbox is enough to consider email usable for the demo.
        inbox = self.env['email.account'].sudo().search_count([
            ('active', '=', True),
            ('email', '!=', False),
        ])
        outgoing = self.env['ir.mail_server'].sudo().search_count([])
        return bool(inbox or outgoing)

    def _load_demo_catalog(self):
        # Every record is looked up before being created. Categories, request
        # notes and template names were Portuguese in older versions, so the
        # old value is accepted too; otherwise a second click after an upgrade
        # would duplicate rows already stored.
        added = []
        categories = {}
        Category = self.env['it.resource.need.category']
        for name, legacy in (('Access', 'Acesso'), ('Equipment', 'Equipamento'), ('License', 'Licença')):
            category = Category.search(['|', ('name', '=', name), ('name', '=', legacy)], limit=1)
            if not category:
                category = Category.create({'name': name})
                added.append(name)
            categories[name] = category
        needs = [
            ('VPN access', 'demo_vpn', 'Access', True, False, False, 'Connect to the company network from outside.'),
            ('Notebook for collaborator', 'demo_notebook', 'Equipment', False, True, False, 'Computer for someone who is starting.'),
            ('Software license', 'demo_licenca', 'License', False, False, True, 'Paid software that a third party authorizes.'),
            ('Headset', 'demo_headset', 'Equipment', False, False, False, 'Headphones for meetings.'),
        ]
        Need = self.env['it.resource.need']
        for name, code, category_name, approve_ti, approve_board, approve_third, description in needs:
            if Need.search([('code', '=', code)], limit=1):
                continue
            Need.create({
                'name': name,
                'code': code,
                'category_id': categories[category_name].id,
                'description': description,
                'approve_ti': approve_ti,
                'approve_board': approve_board,
                'approve_third': approve_third,
            })
            added.append(name)
        Item = self.env['it.resource.item']
        items = [
            ('Headset', 'demo_headset_item', 'physical', 'equipment', 'quantity', 12, 'Headphones for meetings.'),
            ('Notebook', 'demo_notebook_item', 'physical', 'equipment', 'unit', 0, 'Laptop computer with a serial number.'),
            ('Corporate VPN', 'demo_vpn_item', 'virtual', 'vpn', 'unit', 0, 'Remote access, one login per person.'),
        ]
        created_items = {}
        for name, code, item_type, category, tracking, qty, description in items:
            item = Item.search([('code', '=', code)], limit=1)
            if not item:
                item = Item.create({
                    'name': name,
                    'code': code,
                    'item_type': item_type,
                    'category': category,
                    'tracking': tracking,
                    'qty_on_hand': qty,
                    'description': description,
                })
                added.append(name)
            created_items[code] = item
        Unit = self.env['it.resource.unit']
        for serial, code in (('NB-DEMO-001', 'demo_notebook_item'), ('VPN-DEMO-001', 'demo_vpn_item')):
            if Unit.search([('name', '=', serial)], limit=1):
                continue
            Unit.create({
                'name': serial,
                'item_id': created_items[code].id,
            })
            added.append(serial)
        Request = self.env['it.resource.request']
        samples = (
            ('Demo: headset still being requested', 'Demonstração: headset em solicitação', 'demo_headset', False),
            ('Demo: notebook already submitted', 'Demonstração: notebook já enviado', 'demo_notebook', True),
        )
        for note, legacy, code, submit in samples:
            if Request.search(['|', ('note', '=', note), ('note', '=', legacy)], limit=1):
                continue
            order = Request.request_for(False, 0, [{'code': code}], note=note, confirm=False)
            if submit:
                order.action_submit()
            added.append(note)
        return added

    def _load_demo_mail(self):
        # Only stores the texts; nothing is sent. The templates are created
        # out of use so the demo never emails real approvers. The placeholder
        # names inside the bodies are the fixed keys understood by the renderer.
        self.ensure_one()
        templates = [
            (
                'ti',
                'Demo: IT approval',
                'Demonstração: aprovação da TI',
                'text',
                'Request {{{pedido}}}.\nNeeds: {{{necessidades}}}.\nThe decision is still made in the system.',
                False,
            ),
            (
                'board',
                'Demo: board approval',
                'Demonstração: aprovação da diretoria',
                'text',
                'Request {{{pedido}}}.\nNeeds: {{{necessidades}}}.\nThe decision is still made in the system.',
                False,
            ),
            (
                'third',
                'Demo: third-party approval',
                'Demonstração: aprovação de terceiros',
                'text',
                'Request {{{pedido}}}.\nNeeds: {{{necessidades}}}.\n'
                'Reply with a single line containing {{{aprovar}}} or {{{recusar}}}.',
                'aprovador.demo@example.com',
            ),
        ]
        Template = self.env['it.resource.approval.template']
        created = False
        for kind, name, legacy, body_format, body, email_to in templates:
            if Template.search([
                ('setting_id', '=', self.id),
                '|', ('name', '=', name), ('name', '=', legacy),
            ], limit=1):
                continue
            Template.create({
                'setting_id': self.id,
                'name': name,
                'kind': kind,
                'body_format': body_format,
                'body': body,
                'email_to': email_to,
                'approve_token': 'APROVADO' if kind == 'third' else False,
                'refuse_token': 'RECUSADO' if kind == 'third' else False,
                'in_use': False,
            })
            created = True
        return created
