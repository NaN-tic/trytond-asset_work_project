# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all___ = ['Project']
__metaclass__ = PoolMeta


class Project:
    __name__ = 'work.project'
    asset = fields.Many2One('asset', 'Asset', required=True,
        select=True)
