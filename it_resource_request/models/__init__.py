"""Persistent models of the IT resource request module.

The import order matters: models referenced by relational fields of later
models (catalog, access, approval templates) are registered first.
"""
from . import it_resource_item
from . import it_resource_unit
from . import it_resource_assignment
from . import it_resource_need
from . import it_resource_access
from . import it_resource_approval_template
from . import it_resource_setting
from . import it_resource_approval
from . import it_resource_term
from . import it_resource_request
from . import it_resource_request_line
