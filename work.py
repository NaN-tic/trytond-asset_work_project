# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool


__all___ = ['Project', 'ShipmentWork', 'ContractLine', 'Contract']


class Project:
    __name__ = 'work.project'
    __metaclass__ = PoolMeta

    asset = fields.Many2One('asset', 'Asset', select=True)
    contract_lines = fields.One2Many('contract.line', 'project',
        'Contract Lines',
        domain=[
            ('asset', '=', Eval('asset')),
            ],
        add_remove=[
            ('work_project', '=', None),
            ],
        depends=['asset'])
    contract = fields.Function(fields.Many2One('contract', 'Contract'),
        'get_contract', searcher='search_contract')

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        cls.work_shipments.context.update({
                'asset': Eval('asset'),
                })
        pool = Pool()
        Asset = pool.get('asset')
        # If asset_owner module is installed we can add this domain
        if hasattr(Asset, 'owner'):
            cls.asset.domain = [
                ('current_owner', '=', Eval('party')),
                ]
            cls.asset.depends.append('party')

    def get_contract(self, name):
        return self.contract_lines and self.contract_lines[0].id

    @classmethod
    def search_contract(cls, name, clause):
        contract = clause[2]
        ContractLine = Pool().get('contract.line')
        lines = ContractLine.search([('contract', 'in', contract)])
        projects = [x.work_project.id for x in lines if x.work_project]
        return [('id', 'in', projects)]

    @classmethod
    def get_amount_to_invoice(cls, projects, names):
        res = super(Project, cls).get_amount_to_invoice(projects, names)
        ZERO = Decimal('0.00')

        for project in projects:
            amount_to_invoice = res['amount_to_invoice'].get(project.id, ZERO)
            invoiced_amount = res['invoiced_amount'].get(project.id, ZERO)
            for line in project.contract_lines:
                for consumption in line.consumptions:
                    if consumption.invoice_lines:
                        for invoice_line in consumption.invoice_lines:
                            invoiced_amount += invoice_line.amount
                        for credit_line in consumption.credit_lines:
                            invoiced_amount -= invoice_line.amount
                    else:
                        amount_to_invoice += \
                            consumption.get_amount_to_invoice()

            res['amount_to_invoice'][project.id] = amount_to_invoice
            res['invoiced_amount'][project.id] = invoiced_amount
        return res


class ShipmentWork:
    __name__ = 'shipment.work'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(ShipmentWork, cls).__setup__()
        if 'asset' not in cls.work_project.depends:
            cls.work_project.domain.append(If(Bool(Eval('asset')),
                    ('asset', '=', Eval('asset')), ()))
            cls.work_project.depends.append('asset')


class Contract:
    __name__ = 'contract'
    __metaclass__ = PoolMeta

    projects = fields.Function(fields.One2Many('work.project', None,
            'Projects'),
        'get_projects', searcher='search_projects')

    def get_projects(self, name):
        projects = set()
        for line in self.lines:
            if line.work_project:
                projects.add(line.work_project.id)
        return list(projects)

    @classmethod
    def search_projects(cls, name, clause):
        return [('lines.projects',) + tuple(clause[1:])]

    @classmethod
    def confirm(cls, contracts):
        super(Contract, cls).confirm(contracts)
        ContractLine = Pool().get('contract.line')
        lines = []
        for contract in contracts:
            lines += contract.lines
        ContractLine.create_projects(lines)


class ContractLine:
    __name__ = 'contract.line'
    __metaclass__ = PoolMeta

    work_project = fields.Many2One('work.project', 'Project', select=True,
        domain=[
            ('asset', '=', Eval('asset')),
            ('maintenance', '=', True),
            ],
        depends=['asset'])

    def get_shipment_work(self, planned_date):
        shipment = super(ContractLine, self).get_shipment_work(planned_date)
        shipment.work_project = self.work_project
        return shipment

    def get_projects(self):
        pool = Pool()
        Project = pool.get('work.project')

        if self.work_project or not self.asset:
            return

        if not self.asset.current_owner:
            self.raise_user_error('no_asset_owner', self.asset.rec_name)

        project = Project.search([
                ('asset', '=', self.asset.id),
                ('maintenance', '=', True),
                ])
        if project:
            self.project = project[0].id
            self.save()
            return

        project = Project()
        project.company = self.contract.company
        project.party = self.asset.current_owner
        project.asset = self.asset
        project.maintenance = True
        project.start_date = self.contract.start_date
        project.end_date = self.contract.end_date if self.contract.end_date \
            else None
        project.contract_lines = [self]
        return project

    @classmethod
    def create_projects(cls, lines):
        pool = Pool()
        Project = pool.get('work.project')
        new_projects = {}
        for line in lines:
            if not line.project and line.asset and line.asset in new_projects:
                new_projects[line.asset].contract_lines += (line,)
            else:
                project = line.get_projects()
                if project:
                    new_projects[line.asset] = project
        if new_projects:
            Project.create([p._save_values for p in new_projects.values()])
