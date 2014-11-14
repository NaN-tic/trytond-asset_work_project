# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval

__all___ = ['Project', 'Maintenance']
__metaclass__ = PoolMeta


class Project:
    __name__ = 'work.project'
    asset = fields.Many2One('asset', 'Asset', required=True,
        select=True)
    asset_maintenances = fields.One2Many('asset.maintenance', 'reference',
        'Maintenances', size=1)
    category = fields.Function(fields.Many2One('asset.maintenance.category',
            'Category',
            states={
                'required': Bool(Eval('maintenance')),
                'invisible': ~Bool(Eval('maintenance')),
                },
            depends=['maintenance']),
        'get_maintenance', setter='set_maintenance',
        searcher='search_maintenance')
    date_planned = fields.Function(fields.Date('Planned Date',
            states={
                'invisible': ~Bool(Eval('maintenance')),
                },
            depends=['maintenance']),
        'get_maintenance', setter='set_maintenance',
        searcher='search_maintenance')
    date_start = fields.Function(fields.Date('Start Date',
            states={
                'invisible': ~Bool(Eval('maintenance')),
                },
            depends=['maintenance']),
        'get_maintenance', setter='set_maintenance',
        searcher='search_maintenance')
    date_done = fields.Function(fields.Date('Done Date',
            states={
                'invisible': ~Bool(Eval('maintenance')),
                },
            depends=['maintenance']),
        'get_maintenance', setter='set_maintenance',
        searcher='search_maintenance')
    date_next = fields.Function(fields.Date('Next maintenance',
            states={
                'invisible': ~Bool(Eval('maintenance')),
                },
            depends=['maintenance']),
        'get_maintenance', setter='set_maintenance',
        searcher='search_maintenance')

    @classmethod
    def get_maintenance(cls, projects, names):
        pool = Pool()
        Maintenance = pool.get('asset.maintenance')
        res = {}
        for name in names:
            res[name] = dict((m.id, None) for m in projects)

        for maintenance in Maintenance.search([
                    ('reference', 'in', [str(m) for m in projects]),
                    ]):
            project = maintenance.reference.id
            for name in names:
                value = getattr(maintenance, name)
                if isinstance(value, ModelSQL):
                    value = value.id
                res[name][project] = value
        return res

    @classmethod
    def set_maintenance(cls, projects, name, value):
        pool = Pool()
        Maintenance = pool.get('asset.maintenance')
        to_write = []
        to_create = []
        for project in projects:
            if not project.maintenance:
                continue
            if not project.asset_maintenances:
                to_create.append(project.asset_maintenance_vals(
                        {name: value}))
            else:
                to_write.extend(project.asset_maintenances)
        if to_create:
            Maintenance.create(to_create)
        if to_write:
            Maintenance.write(to_write, {
                    name: value,
                    })

    @classmethod
    def search_maintenance(cls, name, clause):
        return [('asset_maintenances.%s' % name,) + tuple(clause[1:])]


class Maintenance:
    __name__ = 'asset.maintenance'

    @classmethod
    def _get_reference(cls):
        references = super(Maintenance, cls)._get_reference()
        references.append('work.project')
        return references
