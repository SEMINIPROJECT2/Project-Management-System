"""Write machine-readable outcomes while retaining Django's normal test runner."""
import json
import os
from pathlib import Path
import time
import unittest

from django.test.runner import DiscoverRunner


class ReportingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.perf_counter()
        super().startTest(test)

    def record(self, test, status, detail=''):
        self.records.append({
            'id': test.id(), 'description': test.shortDescription() or '',
            'status': status, 'detail': detail,
            'seconds': round(time.perf_counter() - self.started.get(test.id(), time.perf_counter()), 6),
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failed', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error', self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped', reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.record(test, 'failed_subtest', self._exc_info_to_string(err, test))


class Part3TestRunner(DiscoverRunner):
    def get_resultclass(self):
        return ReportingResult

    def run_suite(self, suite, **kwargs):
        started = time.perf_counter()
        result = super().run_suite(suite, **kwargs)
        target = Path(os.environ.get('PART3_RESULTS_PATH', 'docs/part3/evidence/test_results.json'))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            'tests_run': result.testsRun, 'failures': len(result.failures),
            'errors': len(result.errors), 'skipped': len(result.skipped),
            'seconds': round(time.perf_counter() - started, 6),
            'records': result.records,
        }, indent=2) + '\n')
        return result
