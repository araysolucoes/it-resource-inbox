# -*- coding: utf-8 -*-
"""Access screen of the module: one row per user with a level and menu tabs.

Instead of asking administrators to combine several security groups by hand,
this screen translates a visibility level and a set of tabs into the module
groups of the user, leaving every other group of the account untouched.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ItResourceAccessTab(models.Model):
    """Menu tab of the module and the security group that opens it."""

    _name = 'it.resource.access.tab'
    _description = 'IT module tab'
    _order = 'sequence, id'

    name = fields.Char(string='Tab', required=True)
    code = fields.Selection(
        [
            ('request', 'Requests'),
            ('catalog', 'Catalog'),
            ('use', 'In use'),
            ('config', 'Settings'),
        ],
        string='Code',
        required=True,
    )
    sequence = fields.Integer(default=10)
    group_id = fields.Many2one(
        'res.groups',
        string='Tab group',
        required=True,
        ondelete='restrict',
    )


class ItResourceAccess(models.Model):
    """Access of one user to the module: what they see and which tabs they open."""

    _name = 'it.resource.access'
    _description = 'IT module access'
    _order = 'user_id'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='Name',
        required=True,
        ondelete='cascade',
        domain="[('share', '=', False)]",
    )
    login = fields.Char(
        string='Login',
        related='user_id.login',
        readonly=True,
    )
    level = fields.Selection(
        [
            ('own', 'Only their own requests'),
            ('directed', 'Directed to them'),
            ('all', 'All'),
        ],
        string='Access level',
        required=True,
        default='own',
        help='What this person sees in the request list.',
    )
    tab_ids = fields.Many2many(
        'it.resource.access.tab',
        'it_resource_access_tab_rel',
        'access_id',
        'tab_id',
        string='Access group',
        help='Menu tabs this person can open.',
    )

    _sql_constraints = [
        (
            'it_resource_access_user_unique',
            'unique(user_id)',
            'This user is already in the access list.',
        ),
    ]

    @api.constrains('tab_ids')
    def _check_tabs(self):
        for access in self:
            if not access.tab_ids:
                raise UserError(_('Choose at least one tab in the access group.'))

    @api.model_create_multi
    def create(self, vals_list):
        """Create the access rows and push them to the user groups."""
        records = super(ItResourceAccess, self).create(vals_list)
        if not self.env.context.get('skip_access_apply'):
            records._apply()
        return records

    def write(self, vals):
        """Save the access rows and push the new level and tabs to the user groups."""
        result = super(ItResourceAccess, self).write(vals)
        if not self.env.context.get('skip_access_apply'):
            self._apply()
        return result

    def unlink(self):
        """Delete the access rows and remove the module groups from those users."""
        users = self.mapped('user_id')
        result = super(ItResourceAccess, self).unlink()
        if users:
            self._clear_module_groups(users)
        return result

    def _level_group(self):
        self.ensure_one()
        xmlids = {
            'own': 'it_resource_request.group_it_resource_user',
            'directed': 'it_resource_request.group_it_level_directed',
            'all': 'it_resource_request.group_it_resource_manager',
        }
        return self.env.ref(xmlids[self.level])

    @api.model
    def _module_groups(self):
        # Only these groups are managed by the access screen. Any other group
        # the user has (from other apps) must survive a save on this screen.
        xmlids = [
            'it_resource_request.group_it_resource_user',
            'it_resource_request.group_it_level_directed',
            'it_resource_request.group_it_resource_manager',
            'it_resource_request.group_it_approval_ti',
            'it_resource_request.group_it_approval_board',
            'it_resource_request.group_it_tab_request',
            'it_resource_request.group_it_tab_catalog',
            'it_resource_request.group_it_tab_use',
            'it_resource_request.group_it_tab_config',
        ]
        return self.env['res.groups'].browse([self.env.ref(xmlid).id for xmlid in xmlids])

    def _apply(self, replace=True):
        # Writes the level and tabs into the user groups. With replace=True the
        # module groups are reset first so a lowered level really takes effect;
        # replace=False is used by the initial sync to avoid removing groups
        # (such as Approval 1/2) that were assigned before this screen existed.
        for access in self:
            user = access.user_id.sudo()
            if not user:
                continue
            commands = []
            if replace:
                commands.extend((3, group.id) for group in self._module_groups())
            commands.append((4, access._level_group().id))
            commands.extend((4, tab.group_id.id) for tab in access.tab_ids if tab.group_id)
            user.write({'groups_id': commands})

    @api.model
    def _clear_module_groups(self, users):
        commands = [(3, group.id) for group in self._module_groups()]
        users.sudo().write({'groups_id': commands})

    @api.model
    def _guess_level(self, user):
        if user.has_group('it_resource_request.group_it_resource_manager'):
            return 'all', ['request', 'catalog', 'use', 'config']
        if user.has_group('it_resource_request.group_it_approval_ti') or user.has_group(
            'it_resource_request.group_it_approval_board'
        ):
            return 'directed', ['request']
        if user.has_group('it_resource_request.group_it_resource_user'):
            return 'own', ['request', 'catalog', 'use']
        return False, []

    @api.model
    def _sync_from_groups(self):
        # Users who already worked with the module before the access screen
        # existed get a row reflecting their current groups, so administrators
        # see everyone in one place without losing any permission.
        tabs = {tab.code: tab for tab in self.env['it.resource.access.tab'].search([])}
        users = self.env['res.users'].search([('share', '=', False)])
        for user in users:
            if self.search([('user_id', '=', user.id)], limit=1):
                continue
            level, codes = self._guess_level(user)
            if not level:
                continue
            chosen = [tabs[code].id for code in codes if code in tabs]
            if not chosen:
                continue
            access = self.with_context(skip_access_apply=True).create({
                'user_id': user.id,
                'level': level,
                'tab_ids': [(6, 0, chosen)],
            })
            access._apply(replace=False)
