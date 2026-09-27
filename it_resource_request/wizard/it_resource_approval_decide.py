# -*- coding: utf-8 -*-
"""Wizard where an internal approver approves or refuses a pending approval."""
from odoo import fields, models


class ItResourceApprovalDecide(models.TransientModel):
    """Collects the decision and the notes before applying them to the approval."""

    _name = 'it.resource.approval.decide'
    _description = 'Decide IT approval'

    approval_id = fields.Many2one(
        'it.resource.approval',
        string='Approval',
        required=True,
        domain=[('state', '=', 'pending'), ('kind', '!=', 'third')],
    )
    decision = fields.Selection(
        [('approved', 'Approve'), ('refused', 'Refuse')],
        string='Decision',
        required=True,
        default='approved',
    )
    note = fields.Text(
        string='Notes',
        help='When approving, record conditions or the suggested item. When refusing, the reason is mandatory.',
    )

    def action_apply(self):
        """Apply the decision and open the request in its new stage."""
        self.ensure_one()
        self.approval_id._decide(self.decision, self.note)
        return self.approval_id.request_id._open_stage()
