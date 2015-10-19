# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Bool


__all___ = ['Project', 'ShipmentWork', 'ContractLine', 'Contract']
__metaclass__ = PoolMeta


class Project:
    __name__ = 'work.project'

    asset = fields.Many2One('asset', 'Asset', select=True)
    contract_lines = fields.One2Many('contract.line', 'project',
        'Contract Lines',
        domain=[
            ('asset', '=', Eval('asset')),
            ],
        add_remove=[
            ('project', '=', None),
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
                ('owner', '=', Eval('party')),
                ]
            cls.asset.depends.append('party')

    def get_contract(self, name):
        return self.contract_lines and self.contract_lines[0].id

    @classmethod
    def search_contract(cls, name, clause):
        contract = clause[2]
        ContractLine = Pool().get('contract.line')
        lines = ContractLine.search([('contract', 'in', contract)])
        projects = [x.project.id for x in lines if x.project]
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

    @classmethod
    def __setup__(cls):
        super(ShipmentWork, cls).__setup__()
        if 'asset' not in cls.project.depends:
            cls.project.domain.append(If(Bool(Eval('asset')),
                    ('asset', '=', Eval('asset')), ()))
            cls.project.depends.append('asset')


class Contract:
    __name__ = 'contract'

    projects = fields.Function(fields.One2Many('work.project', None,
            'Projects'),
        'get_projects', searcher='search_projects')

    def get_projects(self, name):
        projects = set()
        for line in self.lines:
            if line.project:
                projects.add(line.project.id)
        return list(projects)

    @classmethod
    def search_projects(cls, name, clause):
        return [('lines.projects',) + tuple(clause[1:])]

    @classmethod
    def validate_contract(cls, contracts):
        super(Contract, cls).validate_contract(contracts)
        ContractLine = Pool().get('contract.line')
        lines = []
        for contract in contracts:
            lines += contract.lines
        ContractLine.create_projects(lines)


class ContractLine:
    __name__ = 'contract.line'

    project = fields.Many2One('work.project', 'Project', select=True,
        domain=[
            ('asset', '=', Eval('asset')),
            ('maintenance', '=', True),
            ],
        depends=['asset'])

    def get_shipment_work(self, planned_date):
        shipment = super(ContractLine, self).get_shipment_work(planned_date)
        shipment.project = self.project
        return shipment

    def get_projects(self):
        pool = Pool()
        Project = pool.get('work.project')

        if self.project or not self.asset:
            return

        if not self.asset.owner:
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
        project.party = self.asset.owner
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
                new_projects[line.asset].contract_lines += [line]
            else:
                project = line.get_projects()
                if project:
                    new_projects[line.asset] = project
        if new_projects:
            Project.create([p._save_values for p in new_projects.values()])
