# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .work import *


def register():
    Pool.register(
        Project,
        ShipmentWork,
        ContractLine,
        Contract,
        module='asset_work_project', type_='model')
