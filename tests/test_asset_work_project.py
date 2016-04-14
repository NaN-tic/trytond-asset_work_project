# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import (doctest_setup, doctest_teardown,
    doctest_checker)


class TestAssetWorkProject(ModuleTestCase):
    'Test Asset Work Project'
    module = "asset_work_project"


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAssetWorkProject))
    suite.addTests(doctest.DocFileSuite('scenario_asset_work_project.rst',
           setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
           optionflags=doctest.REPORT_ONLY_FIRST_FAILURE,
           checker=doctest_checker))
    return suite
