# -*- coding: utf-8 -*-
"""Approval steps of a request (IT, board and third party).

IT and board approvals are decided inside Odoo by the members of the matching
group. Third-party approvals are decided outside Odoo: the approver replies to
an email and the reply is parsed for the approval or refusal word.
"""
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class ItResourceApproval(models.Model):
    """One approval required by a request and its decision."""

    _name = 'it.resource.approval'
    _description = 'IT request approval'
    _order = 'id'

    request_id = fields.Many2one(
        'it.resource.request',
        string='Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    kind = fields.Selection(
        [
            ('ti', 'IT'),
            ('board', 'Board'),
            ('third', 'Third party'),
        ],
        string='Approver',
        required=True,
    )
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
        ],
        string='Status',
        default='pending',
        required=True,
    )
    allowed_user_ids = fields.Many2many(
        'res.users',
        'it_resource_approval_user_rel',
        'approval_id',
        'user_id',
        string='Who can decide',
        help='Group members at the moment the request entered approval.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Decided by',
        readonly=True,
    )
    note = fields.Text(
        string='Notes',
        help='Text from whoever approved or refused. For an email reply, it is the message body.',
    )
    date = fields.Datetime(string='Decided on', readonly=True)
    email_message_id = fields.Many2one(
        'email.message',
        string='Email sent',
        readonly=True,
    )

    def _user_can_decide(self, user):
        self.ensure_one()
        if user.id == SUPERUSER_ID or user.has_group('it_resource_request.group_it_resource_manager'):
            return True
        if self.kind == 'ti':
            return user.has_group('it_resource_request.group_it_approval_ti')
        if self.kind == 'board':
            return user.has_group('it_resource_request.group_it_approval_board')
        return False

    def _decide(self, decision, note):
        # Internal decision taken from the wizard. Third parties never use this
        # path: their decision only comes from the email reply, so nobody in
        # Odoo can approve on their behalf.
        for approval in self:
            if approval.state != 'pending':
                raise UserError(_('This approval has already been decided.'))
            if approval.kind == 'third':
                raise UserError(_('The third-party approval arrives through the email reply.'))
            user = self.env.user
            if not approval._user_can_decide(user):
                raise UserError(_('You are not in the group that approves this step.'))
            if decision == 'refused' and not (note or '').strip():
                raise UserError(_('When refusing, write the reason in the notes.'))
            approval._apply(decision, note, user)

    def _apply(self, decision, note, user=None):
        self.ensure_one()
        self.write({
            'state': 'approved' if decision == 'approved' else 'refused',
            'note': note or False,
            'user_id': user.id if user else False,
            'date': fields.Datetime.now(),
        })
        # Saving the decision removes the approver from the pending list, so
        # the record rule stops granting access to the request. The request
        # update therefore runs in sudo.
        request = self.request_id.sudo()
        if decision == 'refused':
            request.state = 'nao_aprovado'
            request._post_note(_('Approval refused (%s).') % dict(self._fields['kind'].selection)[self.kind])
            return
        pending = request.approval_ids.filtered(lambda item: item.state == 'pending')
        refused = request.approval_ids.filtered(lambda item: item.state == 'refused')
        if refused:
            request.state = 'nao_aprovado'
        elif not pending:
            request.state = 'aprovado'
            request._post_note(_('All required approvals were accepted.'))

    def action_fetch_reply(self):
        """Fetch the mailbox now and try to read the third-party reply."""
        self.ensure_one()
        if self.kind != 'third':
            raise UserError(_('Only the third-party approval is read from email.'))
        setting = self.env['it.resource.setting'].get_setting()
        account = setting._mail_account(required=False)
        if account:
            account.sudo().fetch_incoming()
        self._read_one_reply(setting)
        return True

    def _read_one_reply(self, setting):
        self.ensure_one()
        if self.state != 'pending' or self.kind != 'third':
            return False
        message = self.env['email.message'].sudo().search([
            ('res_model', '=', 'it.resource.request'),
            ('res_id', '=', self.request_id.id),
            ('direction', '=', 'in'),
        ], order='date desc, id desc', limit=1)
        if not message:
            return False
        template = setting._template_in_use('third')
        if not template:
            return False
        decision = self._classify_reply(
            message.body or '',
            template.approve_token,
            template.refuse_token,
        )
        if not decision:
            return False
        self._apply(decision, message.body or '')
        return True

    @api.model
    def _classify_reply(self, body, approve_token, refuse_token):
        """The word must stand alone at the start of a line.

        Replies usually quote the original message, which contains both words,
        so matching anywhere in the text would give false decisions. Refusal is
        checked first so an ambiguous reply never approves by accident.
        """
        lines = [(line or '').strip().lower() for line in (body or '').splitlines()]

        def hit(token):
            token = (token or '').strip().lower()
            if not token:
                return False
            return any(line == token or line.startswith(token + ' ') for line in lines)

        if hit(refuse_token):
            return 'refused'
        if hit(approve_token):
            return 'approved'
        return False

    @api.model
    def cron_read_replies(self):
        """Scheduled job: fetch the mailbox and read pending third-party replies."""
        setting = self.env['it.resource.setting'].get_setting()
        pending = self.search([('kind', '=', 'third'), ('state', '=', 'pending')])
        if not pending:
            return True
        if setting._mail_account(required=False):
            try:
                setting._mail_account().sudo().fetch_incoming()
            except Exception:
                # A mailbox error must not make the cron fail: the next run
                # retries, and the error is already logged on the email account.
                return True
        for approval in pending:
            approval._read_one_reply(setting)
        return True
