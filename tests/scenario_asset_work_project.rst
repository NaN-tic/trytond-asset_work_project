=============
Sale Scenario
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> tomorrow = datetime.date.today() + relativedelta(days=1)
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([('name', '=', 'asset_work_project')])
    >>> Module.install([module.id], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')


Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']

Create tax::

    >>> tax = set_tax_code(create_tax(Decimal('.10')))
    >>> tax.save()
    >>> invoice_base_code = tax.invoice_base_code
    >>> invoice_tax_code = tax.invoice_tax_code
    >>> credit_note_base_code = tax.credit_note_base_code
    >>> credit_note_tax_code = tax.credit_note_tax_code

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'assets'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('8')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product.template = template
    >>> product.save()

    >>> service_product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'service'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.list_price = Decimal('30')
    >>> template.cost_price = Decimal('10')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> service_product.template = template
    >>> service_product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='remainder')
    >>> payment_term.save()

Create an asset::

    >>> Asset = Model.get('asset')
    >>> AssetOwner = Model.get('asset.owner')
    >>> asset = Asset()
    >>> asset.name = 'Asset'
    >>> asset.product = product
    >>> owner = AssetOwner()
    >>> owner.owner = customer
    >>> owner.asset = asset
    >>> owner.from_date = today
    >>> asset.save()
    >>> owner.save()
    >>> other_asset = Asset()
    >>> other_asset.name = 'Other Asset'
    >>> other_asset.product = product
    >>> other_asset.save()
    >>> owner2 = AssetOwner()
    >>> owner2.owner = customer
    >>> owner2.from_date = today
    >>> owner2.asset = other_asset
    >>> owner2.save()


Configure shipment work::
    >>> Sequence = Model.get('ir.sequence')
    >>> StockConfig = Model.get('stock.configuration')
    >>> stock_config = StockConfig(1)
    >>> shipment_work_sequence, = Sequence.find([
    ...     ('code', '=', 'shipment.work'),
    ...     ])
    >>> stock_config.shipment_work_sequence = shipment_work_sequence
    >>> stock_config.save()


Create daily service::

    >>> Service = Model.get('contract.service')
    >>> service = Service()
    >>> service.product = service_product
    >>> service.name = 'Service'
    >>> service.freq = 'daily'
    >>> service.interval = 1
    >>> service.save()


Models::
    >>> Sequence = Model.get('ir.sequence')
    >>> WorkProjectConfig = Model.get('work.project.configuration')
    >>> work_project_sequence, = Sequence.find([('code','=','work.project')])
    >>> work_project_config = WorkProjectConfig(1)
    >>> work_project_config.project_sequence = work_project_sequence
    >>> work_project_config.save()


Create a contract::

    >>> Contract = Model.get('contract')
    >>> contract = Contract()
    >>> contract.party = customer
    >>> contract.start_date = today
    >>> contract.first_invoice_date = today
    >>> contract.start_period_date = today
    >>> contract.freq = 'monthly'
    >>> contract.interval = 1
    >>> line = contract.lines.new()
    >>> line.service = service
    >>> line.create_shipment_work = True
    >>> line.first_shipment_date = today
    >>> line.start_date = today
    >>> line.asset = asset
    >>> contract.click('confirm')
    >>> contract.state
    u'confirmed'
    >>> contract_line, = contract.lines

A project it's created for the contract::

    >>> project, = contract.projects
    >>> project.asset == asset
    True
    >>> bool(project.maintenance)
    True

Create a shipments::

    >>> create_shipments = Wizard('contract.create_shipments')
    >>> create_shipments.form.date = today + relativedelta(days=+1)
    >>> create_shipments.execute('create_shipments')
    >>> Shipment = Model.get('shipment.work')
    >>> shipments = Shipment.find([])
    >>> shipment = shipments[0]
    >>> shipment.planned_date == today.date()
    True
    >>> shipment.contract_line == contract_line
    True
    >>> shipment.project == project
    True
    >>> shipment.asset == asset
    True

The asset has a maintenance planned for the same date::

    >>> asset.reload()
    >>> asset.shipments[0].planned_date == today.date()
    True

Create another contract for the same asset and check it's linked on the same
contract::

    >>> contract.click('cancel')
    >>> contract.click('draft')
    >>> line = contract.lines.new()
    >>> line.service = service
    >>> line.asset = asset
    >>> line.first_invoice_date = today
    >>> line.start_date = today
    >>> contract.click('validate_contract')
    >>> project, = contract.projects
    >>> len(project.contract_lines)
    2

When linking the same asset in multiple contract lines only one project is
created::

    >>> contract = Contract()
    >>> contract.party = customer
    >>> contract.start_date = today
    >>> contract.start_period_date = today
    >>> contract.freq = 'monthly'
    >>> line = contract.lines.new()
    >>> line.service = service
    >>> line.create_shipment_work = True
    >>> line.first_shipment_date = today
    >>> line.first_invoice_date = today
    >>> line.start_date = today
    >>> line.asset = other_asset
    >>> line = contract.lines.new()
    >>> line.service = service
    >>> line.first_invoice_date = today
    >>> line.start_date = today
    >>> line.asset = other_asset
    >>> contract.click('validate_contract')
    >>> project, = contract.projects
    >>> project.asset == other_asset
    True
    >>> bool(project.maintenance)
    True
    >>> len(project.contract_lines)
    2
    >>> contract.state
    u'validated'
