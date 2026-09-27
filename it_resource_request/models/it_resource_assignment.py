# -*- coding: utf-8 -*-
"""Record of who holds an IT resource, created when a request line is fulfilled."""
from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import UserError


class ItResourceAssignment(models.Model):
    """Delivery of an item (or one of its units) to a user, until it is returned."""

    _name = 'it.resource.assignment'
    _description = 'IT resource assignment'
    _order = 'date desc, id desc'

    item_id = fields.Many2one(
        'it.resource.item', string='Item', required=True, ondelete='restrict',
    )
    user_id = fields.Many2one(
        'res.users', string='User', required=True, ondelete='restrict',
    )
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    line_id = fields.Many2one(
        'it.resource.request.line',
        string='Request line',
        ondelete='set null',
    )
    unit_id = fields.Many2one(
        'it.resource.unit', string='Unit', ondelete='set null',
    )
    date = fields.Datetime(
        string='Delivered on',
        default=fields.Datetime.now,
        required=True,
        help='When the manager fulfilled the line and this person received the resource.',
    )
    returned = fields.Boolean(
        string='Returned',
        default=False,
        help='When checked, the quantity went back to the item or the unit became free again.',
    )
    return_date = fields.Datetime(
        string='Returned on',
        readonly=True,
    )

    def action_return(self):
        """Give the quantity back to the item or free the unit.

        The internal superuser is accepted because the return signature flow
        calls this method in sudo on behalf of the collaborator.
        """
        user = self.env.user
        if user.id != SUPERUSER_ID and not user.has_group(
            'it_resource_request.group_it_resource_manager'
        ):
            raise UserError(_('Only the manager can register the return.'))
        for assignment in self:
            if assignment.returned:
                raise UserError(_('This delivery has already been returned.'))
            if assignment.unit_id:
                assignment.unit_id.write({
                    'state': 'available',
                    'assigned_user_id': False,
                    'assigned_line_id': False,
                })
            elif assignment.item_id.tracking == 'quantity':
                assignment.item_id.qty_on_hand += assignment.quantity
            assignment.write({
                'returned': True,
                'return_date': fields.Datetime.now(),
            })
        return True
