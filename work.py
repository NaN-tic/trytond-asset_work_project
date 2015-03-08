# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval


__all___ = ['Project', 'ContractLine', 'Contract']
__metaclass__ = PoolMeta


class Project:
    __name__ = 'work.project'

    asset = fields.Many2One('asset', 'Asset', select=True)
    contract_line = fields.Many2One('contract.line', 'Contract Line')
    contract = fields.Function(fields.Many2One('contract', 'Contract'),
        'get_contract', searcher='search_contract')

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        cls.work_shipments.context.update({
                'asset': Eval('asset'),
                })

    def get_contract(self, name):
        return self.contract_line and self.contract_line.id

    @classmethod
    def search_contract(cls, name, clause):
        return [('contract_line.projects',) + tuple(clause[1:])]


class Contract:
    __name__ = 'contract'

    projects = fields.Function(fields.One2Many('work.project', None,
            'Projects'),
        'get_projects', searcher='search_projects')

    def get_projects(self, name):
        return list(set(p.id for l in self.lines for p in l.projects))

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

    projects = fields.One2Many('work.project', 'contract_line', 'Projects',
        domain=[
            ('asset', '=', Eval('asset')),
            ('maintenance', '=', True),
            ],
        depends=['asset'])

    def get_projects(self):
        pool = Pool()
        Project = pool.get('work.project')
        if self.projects or not self.asset:
            return
        if not self.asset.owner:
            self.raise_user_error('no_asset_owner', self.asset.rec_name)
        project = Project()
        project.company = self.contract.company
        project.party = self.asset.owner
        project.asset = self.asset
        project.maintenance = True
        project.start_date = self.contract.start_date
        project.end_date = self.contract.end_date if self.contract.end_date \
            else None
        project.contract_line = self
        return [project]

    @classmethod
    def create_projects(cls, lines):
        pool = Pool()
        Project = pool.get('work.project')
        new_projects = []
        for line in lines:
            projects = line.get_projects()
            if projects:
                new_projects.extend(projects)
        if new_projects:
            Project.create([p._save_values for p in new_projects])
