# -*- coding: utf-8 -*-
"""IT resource request header and its stage workflow.

A request moves through fixed stages (requesting, approval, IT handling,
signature, in use, return). The state keys are stored in the database and
used by record rules, views and other modules, so they stay in Portuguese
even though every label shown to users is English.
"""
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class ItResourceRequest(models.Model):
    """Request for one or more IT needs, opened by a person or another module."""

    _name = 'it.resource.request'
    _description = 'IT resource request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested by',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help='Person who keeps the resource, unless the line names another recipient.',
    )
    expected_date = fields.Datetime(
        string='Needed by',
        default=fields.Datetime.now,
        tracking=True,
        help='Date the person needs to receive it. New lines copy this date.',
    )
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'High')],
        string='Priority',
        default='0',
        tracking=True,
        help='High requests are highlighted so the manager handles them first.',
    )
    note = fields.Text(
        string='Reason for the request',
        help='Why this resource is needed. It helps the manager decide.',
    )
    res_model = fields.Char(
        string='Source module',
        index=True,
        help='Filled when another module opens the request. Links this request to the record over there.',
    )
    res_id = fields.Integer(
        string='Source record number',
        index=True,
        help='Number of the record that asked for the resource, in the source module.',
    )
    collaborator_id = fields.Many2one(
        'res.users',
        string='Collaborator',
        tracking=True,
        help='Person who will receive the resource. The supervisor asks on their behalf. Each line can name another person.',
    )
    line_ids = fields.One2many(
        'it.resource.request.line', 'request_id', string='Request lines',
    )
    line_count = fields.Integer(string='Needs', compute='_compute_line_count')
    stage_label = fields.Char(
        string='Current stage',
        compute='_compute_stage_label',
    )
    approval_ids = fields.One2many(
        'it.resource.approval', 'request_id', string='Approvals',
    )
    pending_ti_user_ids = fields.Many2many(
        'res.users',
        'it_resource_request_pending_ti_user_rel',
        'request_id',
        'user_id',
        string='Waiting for Approval 1',
        compute='_compute_pending_approvers',
        store=True,
    )
    pending_board_user_ids = fields.Many2many(
        'res.users',
        'it_resource_request_pending_board_user_rel',
        'request_id',
        'user_id',
        string='Waiting for Approval 2',
        compute='_compute_pending_approvers',
        store=True,
    )
    signature_ids = fields.One2many(
        'it.resource.signature', 'request_id', string='Signatures',
    )
    state = fields.Selection(
        [
            ('solicitando', 'Requesting'),
            ('solicitado', 'Requested'),
            ('aguardando_aprovacao', 'Waiting for approval'),
            ('aprovado', 'Approved'),
            ('em_andamento', 'In progress'),
            ('alocacao', 'Allocation'),
            ('disponibilidade', 'Availability'),
            ('entregue', 'Delivered (waiting for signature)'),
            ('em_uso', 'In use (signed)'),
            ('devolucao', 'Return (waiting for signature)'),
            ('devolvido', 'Returned'),
            ('cancelado', 'Cancelled'),
            ('nao_aprovado', 'Not approved'),
        ],
        string='Stage',
        default='solicitando',
        required=True,
        tracking=True,
        copy=False,
    )

    def init(self):
        """Migrate the state codes of the first module versions.

        Early versions stored draft/open/done/cancel. Rows still holding those
        codes would not match any selection value and would break the views,
        so they are mapped to the current stage keys on every module load.
        """
        self.env.cr.execute("""
            UPDATE it_resource_request
               SET state = CASE state
                   WHEN 'draft' THEN 'solicitando'
                   WHEN 'open' THEN 'em_andamento'
                   WHEN 'done' THEN 'em_uso'
                   WHEN 'cancel' THEN 'cancelado'
                   ELSE state
               END
             WHERE state IN ('draft', 'open', 'done', 'cancel')
        """)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for order in self:
            order.line_count = len(order.line_ids)

    @api.depends(
        'state',
        'approval_ids.state',
        'approval_ids.kind',
        'approval_ids.allowed_user_ids',
    )
    def _compute_pending_approvers(self):
        # The record rules of Approval 1 and 2 read these stored lists, so an
        # approver must only appear while the request still waits for them.
        # Once they decide (or the request leaves the approval stage) the
        # request disappears from their view.
        empty = [(5, 0, 0)]
        for order in self:
            if order.state != 'aguardando_aprovacao':
                order.pending_ti_user_ids = empty
                order.pending_board_user_ids = empty
                continue
            ti = order.approval_ids.filtered(
                lambda item: item.kind == 'ti' and item.state == 'pending'
            )
            board = order.approval_ids.filtered(
                lambda item: item.kind == 'board' and item.state == 'pending'
            )
            order.pending_ti_user_ids = [(6, 0, ti.mapped('allowed_user_ids').ids)]
            order.pending_board_user_ids = [(6, 0, board.mapped('allowed_user_ids').ids)]

    @api.model
    def _refresh_access_snapshot(self):
        # Demo templates must never stay in use: they would send placeholder
        # text for real requests. Older versions named them "Demonstração:",
        # newer ones "Demo:", so both prefixes are matched.
        templates = self.env['it.resource.approval.template'].search([
            '|',
            ('name', '=like', 'Demonstração:%'),
            ('name', '=like', 'Demo:%'),
            ('in_use', '=', True),
        ])
        if templates:
            templates.with_context(skip_in_use=True).write({'in_use': False})
        # Approval 1 and 2 no longer imply the Requester group. Users that got
        # Requester only through that old implication are removed from it, so
        # the Requester record rule does not widen or narrow their view.
        user_group = self.env.ref('it_resource_request.group_it_resource_user')
        manager = self.env.ref('it_resource_request.group_it_resource_manager')
        approvers = (
            self.env.ref('it_resource_request.group_it_approval_ti').users
            | self.env.ref('it_resource_request.group_it_approval_board').users
        )
        drop = approvers.filtered(
            lambda user: user not in manager.users and user in user_group.users
        )
        if drop:
            user_group.sudo().write({'users': [(3, user.id) for user in drop]})
        # The pending approver lists are stored; recompute them so existing
        # requests follow the current rules right after an upgrade.
        orders = self.search([])
        if not orders:
            return
        self.env.add_to_compute(self._fields['pending_ti_user_ids'], orders)
        self.env.add_to_compute(self._fields['pending_board_user_ids'], orders)
        orders.recompute()

    @api.depends('state')
    def _compute_stage_label(self):
        # The stat button in the form shows the stage name instead of the line
        # count, so users see at a glance where the request stands.
        labels = dict(self._fields['state'].selection)
        for order in self:
            order.stage_label = labels.get(order.state) or ''

    @api.model
    def request_for(self, res_model, res_id, lines, requested_by=None,
                    expected_date=None, note=None, confirm=False):
        """Open a request on behalf of another module.

        Each line accepts ``need_id`` or the need ``code``, plus ``quantity``
        and ``collaborator_id``. With ``confirm=True`` the request is submitted
        and sent to approval; when no approval is required it ends up approved.
        """
        prepared = []
        Need = self.env['it.resource.need']
        for line in lines:
            if line.get('need_id'):
                need = Need.browse(line['need_id']).exists()
                if not need:
                    raise UserError(_('The IT need does not exist.'))
            else:
                need = Need.get_by_code(line.get('code'))
            vals = {
                'need_id': need.id,
                'quantity': line.get('quantity') or 1.0,
            }
            if line.get('collaborator_id'):
                vals['collaborator_id'] = line['collaborator_id']
            if line.get('assignee_id'):
                vals['collaborator_id'] = line['assignee_id']
            prepared.append((0, 0, vals))
        order = self.create({
            'requested_by': requested_by or self.env.uid,
            'expected_date': expected_date or fields.Datetime.now(),
            'note': note,
            'res_model': res_model,
            'res_id': res_id or 0,
            'line_ids': prepared,
        })
        if confirm:
            order.action_submit()
            order.action_request_approval()
        return order

    @api.model
    def for_record(self, res_model, res_id):
        """Return the requests linked to a record of another module."""
        return self.search([
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
        ])

    def action_open_origin(self):
        """Open the record of the source module that created this request."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_('This request is not linked to a record of another module.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source record'),
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Assign the next sequence number to requests created without one."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('it.resource.request')
                    or _('New')
                )
        return super().create(vals_list)

    def unlink(self):
        """Only allow deleting requests that were never submitted, except for managers."""
        for order in self:
            if order.state != 'solicitando' and not self.env.user.has_group(
                'it_resource_request.group_it_resource_manager'
            ):
                raise UserError(_('A request can only be deleted while it is still in Requesting.'))
        return super().unlink()

    def _post_note(self, body):
        # Approvers do not always have an email on their contact. The chatter
        # requires a sender address, and a missing one must not block the
        # approval decision, hence the local fallback address.
        author = self.env.user
        email_from = author.email or author.partner_id.email or 'ti@localhost'
        self.message_post(
            body=body,
            email_from=email_from,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _check_manager(self):
        # The internal superuser (id 1) is not member of any group but must be
        # able to run every stage, for example from server actions or crons.
        user = self.env.user
        if user.id != SUPERUSER_ID and not user.has_group(
            'it_resource_request.group_it_resource_manager'
        ):
            raise UserError(_('Only the all_perms group can perform this step.'))

    def action_submit(self):
        """Move the request from Requesting to Requested after validating its lines."""
        for order in self:
            if order.state != 'solicitando':
                raise UserError(_('Only a request in Requesting can be submitted.'))
            if not order.line_ids:
                raise UserError(_('Add at least one need.'))
            for line in order.line_ids:
                if not line.need_id:
                    raise UserError(_('Every line needs a need.'))
                if not line.collaborator_id:
                    line.collaborator_id = order.collaborator_id or order.requested_by
                    line.assignee_id = line.collaborator_id
            order.state = 'solicitado'
        return self._open_stage() if len(self) == 1 else True

    def _open_stage(self):
        # After each transition the user lands on the menu of the stage the
        # request is now in, instead of the list they came from, so the
        # breadcrumb matches where the request can be found later.
        self.ensure_one()
        xmlids = {
            'solicitando': 'action_it_resource_request_draft',
            'solicitado': 'action_it_resource_request_draft',
            'aguardando_aprovacao': 'action_it_resource_request_open',
            'aprovado': 'action_it_resource_request_progress',
            'em_andamento': 'action_it_resource_request_progress',
            'alocacao': 'action_it_resource_request_progress',
            'disponibilidade': 'action_it_resource_request_progress',
            'entregue': 'action_it_resource_request_sign',
            'devolucao': 'action_it_resource_request_sign',
            'em_uso': 'action_it_resource_request_done',
            'devolvido': 'action_it_resource_request_cancel',
            'cancelado': 'action_it_resource_request_cancel',
            'nao_aprovado': 'action_it_resource_request_cancel',
        }
        action = self.env.ref('it_resource_request.%s' % xmlids[self.state]).read()[0]
        form_view = self.env.ref('it_resource_request.view_it_resource_request_form')
        action.update({
            'res_id': self.id,
            'view_mode': 'form,kanban,tree',
            'views': [(form_view.id, 'form'), (False, 'kanban'), (False, 'tree')],
            'target': 'current',
        })
        return action

    def action_request_approval(self):
        """Create the approvals required by the needs and notify the approvers.

        When no need requires approval the request goes straight to Approved.
        """
        Approval = self.env['it.resource.approval']
        Setting = self.env['it.resource.setting']
        for order in self:
            if order.state != 'solicitado':
                raise UserError(_('Ask for approval when the request is in Requested.'))
            order.approval_ids.filtered(lambda item: item.state == 'pending').unlink()
            setting = Setting.get_setting()
            kinds = set()
            for line in order.line_ids:
                if line.need_id.approve_ti:
                    kinds.add('ti')
                if line.need_id.approve_board:
                    kinds.add('board')
                if line.need_id.approve_third:
                    kinds.add('third')
            if not kinds:
                order.state = 'aprovado'
                continue
            if 'ti' in kinds and not order._approvers('ti'):
                raise UserError(_('Add someone to the Approval 1 group.'))
            if 'board' in kinds and not order._approvers('board'):
                raise UserError(_('Add someone to the Approval 2 group.'))
            if 'third' in kinds:
                setting._check_third_ready()
            for kind in ('ti', 'board', 'third'):
                if kind not in kinds:
                    continue
                vals = {
                    'request_id': order.id,
                    'kind': kind,
                }
                if kind != 'third':
                    vals['allowed_user_ids'] = [(6, 0, order._approvers(kind).ids)]
                approval = Approval.create(vals)
                if kind == 'third':
                    order._send_third_approval(approval, setting)
                else:
                    order._send_internal_approval(approval, setting, kind)
            order.state = 'aguardando_aprovacao'
        return self._open_stage() if len(self) == 1 else True

    def _approvers(self, kind):
        # Approvers come from the security group, not from a list saved in the
        # settings, so adding or removing someone takes effect immediately.
        xmlid = {
            'ti': 'it_resource_request.group_it_approval_ti',
            'board': 'it_resource_request.group_it_approval_board',
        }[kind]
        return self.env.ref(xmlid).users

    def _approval_values(self, setting, kind):
        # The placeholder keys (pedido, necessidades, aprovar, recusar) are
        # referenced by templates already stored in the database, so they are
        # kept as they are.
        needs = ', '.join(self.line_ids.mapped('need_id.name'))
        template = setting._template_in_use(kind)
        values = {
            'pedido': self.name,
            'necessidades': needs,
        }
        if template and kind == 'third':
            values['aprovar'] = template.approve_token or ''
            values['recusar'] = template.refuse_token or ''
        return template, values

    def _send_third_approval(self, approval, setting):
        self.ensure_one()
        template, values = self._approval_values(setting, 'third')
        account = setting._mail_account()
        message = account.send_for_record(
            'it.resource.request',
            self.id,
            template.email_to,
            _('Approval of request %s') % self.name,
            template.render_body(self, values),
            body_format=template.body_format,
        )
        approval.email_message_id = message.id

    def _send_internal_approval(self, approval, setting, kind):
        # The email is only a courtesy notice: without a template in use the
        # internal approvers still decide through the button in Odoo.
        self.ensure_one()
        template, values = self._approval_values(setting, kind)
        if not template:
            return
        account = setting._mail_account()
        for user in approval.allowed_user_ids:
            email = user.email or user.partner_id.email
            if not email:
                continue
            account.send_for_record(
                'it.resource.request',
                self.id,
                email,
                _('Approval of request %s') % self.name,
                template.render_body(self, values),
                body_format=template.body_format,
            )

    def action_open_decide(self):
        """Open the decision wizard on the first internal approval the user can decide."""
        self.ensure_one()
        user = self.env.user
        pending = self.approval_ids.filtered(
            lambda item: item.state == 'pending' and item.kind != 'third' and item._user_can_decide(user)
        )
        if not pending:
            raise UserError(_('There is no internal approval pending for you on this request.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Decide approval'),
            'res_model': 'it.resource.approval.decide',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_approval_id': pending[0].id},
        }

    def action_start(self):
        """Start IT handling of an approved request."""
        self._check_manager()
        for order in self:
            if order.state != 'aprovado':
                raise UserError(_('Only an approved request can be put in progress.'))
            order.state = 'em_andamento'
        return self._open_stage() if len(self) == 1 else True

    def action_to_allocation(self):
        """Open the allocation stage, where IT picks the item of each need."""
        self._check_manager()
        for order in self:
            if order.state != 'em_andamento':
                raise UserError(_('Allocation starts with the request in progress.'))
            order.state = 'alocacao'
        return self._open_stage() if len(self) == 1 else True

    def action_check_availability(self):
        """Compare the chosen items against their available quantity."""
        self._check_manager()
        for order in self:
            if order.state not in ('alocacao', 'disponibilidade'):
                raise UserError(_('Check availability during the allocation stage.'))
            if any(not line.item_id for line in order.line_ids):
                raise UserError(_('Choose the item of each need before checking the stock.'))
            for line in order.line_ids:
                line.availability = 'ok' if line.qty_available >= line.quantity else 'short'
            order.state = 'disponibilidade'
        return self._open_stage() if len(self) == 1 else True

    def action_deliver(self):
        """Create the receipt signatures and wait for the collaborators to sign."""
        self._check_manager()
        Signature = self.env['it.resource.signature']
        for order in self:
            if order.state != 'disponibilidade':
                raise UserError(_('Delivery starts from the availability stage.'))
            short = order.line_ids.filtered(lambda line: line.availability != 'ok')
            if short:
                raise UserError(_('Some needs still have no stock: %s.') % ', '.join(short.mapped('need_id.name')))
            Signature.create_for_lines(order.line_ids, 'receipt')
            order.state = 'entregue'
        return self._open_stage() if len(self) == 1 else True

    def action_start_return(self):
        """Create the return signatures of a resource that is in use."""
        self._check_manager()
        Signature = self.env['it.resource.signature']
        for order in self:
            if order.state != 'em_uso':
                raise UserError(_('The return starts when the resource is in use.'))
            Signature.create_for_lines(order.line_ids, 'return')
            order.state = 'devolucao'
        return self._open_stage() if len(self) == 1 else True

    def _after_signature(self, sign):
        # Stock only moves once every line of the same term type is signed, so
        # a partially signed request never shows a half-delivered state.
        self.ensure_one()
        pending = self.signature_ids.filtered(
            lambda item: item.term_type == sign.term_type and item.state != 'signed'
        )
        if pending:
            return True
        if sign.term_type == 'receipt' and self.state == 'entregue':
            for line in self.line_ids:
                line.sudo()._fulfill_one()
            self.state = 'em_uso'
        elif sign.term_type == 'return' and self.state == 'devolucao':
            assignments = self.line_ids.mapped('assignment_ids').filtered(lambda item: not item.returned)
            if assignments:
                assignments.sudo().action_return()
            self.state = 'devolvido'
        return True

    def action_cancel(self):
        """Cancel a request that has not reached the delivery stages yet."""
        allowed = ('solicitando', 'solicitado', 'aguardando_aprovacao', 'aprovado', 'em_andamento')
        for order in self:
            if order.state not in allowed:
                raise UserError(_('This request can no longer be cancelled at this stage.'))
            order.state = 'cancelado'
        return self._open_stage() if len(self) == 1 else True

    def action_open_my_signature(self):
        """Open the pending term of the current user, or any pending term for managers."""
        self.ensure_one()
        pending = self.signature_ids.filtered(lambda item: item.state == 'pending')
        mine = pending.filtered(lambda item: item.signer_id == self.env.user)
        if mine:
            target = mine[0]
        elif self.env.user.id == SUPERUSER_ID or self.env.user.has_group(
            'it_resource_request.group_it_resource_manager'
        ):
            if not pending:
                raise UserError(_('There is no term waiting for signature.'))
            target = pending[0]
        else:
            raise UserError(_('There is no term waiting for your signature.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sign term'),
            'res_model': 'it.resource.signature',
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'edit'},
        }

    def action_back_to_requesting(self):
        """Reopen a request for editing, discarding its previous approvals."""
        for order in self:
            if order.state not in ('cancelado', 'nao_aprovado', 'solicitado'):
                raise UserError(_('You can only go back to Requesting from Requested, Cancelled or Not approved.'))
            order.approval_ids.unlink()
            order.state = 'solicitando'
        return self._open_stage() if len(self) == 1 else True
