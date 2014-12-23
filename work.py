# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all___ = ['Project', 'ShipmentWork']
__metaclass__ = PoolMeta


class Project:
    __name__ = 'work.project'
    asset = fields.Many2One('asset', 'Asset', select=True)

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        cls.work_shipments.context.update({
                'asset': Eval('asset'),
                })


class ShipmentWork:
    __name__ = 'shipment.work'

    @classmethod
    def default_employee(cls):
        pool = Pool()
        Asset = pool.get('asset')
        asset_id = Transaction().context.get('asset')
        if asset_id:
            asset = Asset(asset_id)
            if hasattr(asset, 'zone') and asset.zone and asset.zone.employee:
                return asset.zone.employee.id
        try:
            return super(ShipmentWork, cls).default_employee()
        except AttributeError:
            return None
