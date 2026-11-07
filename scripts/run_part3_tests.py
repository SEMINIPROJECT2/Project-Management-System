"""Reproduce Part 3 test outcomes and statement/branch coverage evidence."""
import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'part3' / 'evidence'
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
env = os.environ.copy()
for key, value in {'DJANGO_DEBUG': 'true', 'ALLOWED_HOSTS': '127.0.0.1,localhost,testserver', 'RUN_BROWSER_TESTS': '1', 'RUN_PERFORMANCE_TESTS': '1'}.items():
    env.setdefault(key, value)
env.update(PART3_RESULTS_PATH=str(OUT / 'test_results.json'), PART3_BROWSER_EVIDENCE=str(OUT / 'browser'), PART3_LOAD_EVIDENCE=str(OUT / 'concurrent_load.json'))
commands = []


def run(args, name, extra_env=None):
    with (OUT / name).open('w') as output:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, env={**env, **(extra_env or {})}, stdout=output, stderr=subprocess.STDOUT)
    commands.append({'command': 'python ' + ' '.join(args), 'returncode': result.returncode, 'log': name})
    print(name, 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
    return result.returncode


run(['-m', 'coverage', 'erase'], 'coverage_erase.txt')
failed = run(['-m', 'coverage', 'run', 'manage.py', 'test', '--settings=tests.part3_settings', '--testrunner=tests.reporting_runner.Part3TestRunner', '--verbosity=2'], 'full_test_run.txt', {'RUN_PERFORMANCE_TESTS': '0', 'PART3_RESULTS_PATH': str(OUT / 'functional_results.json')})
for args, name in [
    (['-m', 'coverage', 'combine'], 'coverage_combine.txt'),
    (['-m', 'coverage', 'report'], 'coverage_summary.txt'),
    (['-m', 'coverage', 'json', '-o', str(OUT / 'coverage.json')], 'coverage_json.txt'),
    (['-m', 'coverage', 'xml', '-o', str(OUT / 'coverage.xml')], 'coverage_xml.txt'),
    (['-m', 'coverage', 'html'], 'coverage_html.txt'),
    (['manage.py', 'check'], 'django_check.txt'),
    (['manage.py', 'makemigrations', '--check', '--dry-run'], 'migration_check.txt'),
]:
    failed = run(args, name) or failed
# Latency is measured without coverage tracing; tracing overhead is not an
# application response-time characteristic. Retain each run and merge by ID.
failed = run(['manage.py', 'test', 'tests.test_board_performance', 'tests.test_concurrent_performance', '--settings=tests.part3_settings', '--testrunner=tests.reporting_runner.Part3TestRunner', '--verbosity=2'], 'performance_run.txt', {'RUN_PERFORMANCE_TESTS': '1', 'PART3_RESULTS_PATH': str(OUT / 'performance_results.json')}) or failed
functional = json.loads((OUT / 'functional_results.json').read_text())
performance = json.loads((OUT / 'performance_results.json').read_text())
by_id = {r['id']: r for r in functional['records']}
by_id.update({r['id']: r for r in performance['records']})
records = list(by_id.values())
combined = {
    'tests_run': len(records),
    'failures': sum(r['status'] in ('failed', 'failed_subtest') for r in records),
    'errors': sum(r['status'] == 'error' for r in records),
    'skipped': sum(r['status'] == 'skipped' for r in records),
    'seconds': functional['seconds'] + performance['seconds'],
    'runner_method_entries': functional['tests_run'] + performance['tests_run'],
    'runs': {'functional_coverage': {k:v for k,v in functional.items() if k != 'records'}, 'performance_without_tracing': {k:v for k,v in performance.items() if k != 'records'}},
    'records': records,
}
(OUT / 'test_results.json').write_text(json.dumps(combined, indent=2) + '\n')
import django
metadata = {'date': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': platform.python_version(), 'platform': platform.platform(), 'django': django.get_version(), 'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'execution_context': os.environ.get('GITHUB_ACTIONS') and 'GitHub Actions' or 'Local runtime', 'commands': commands}
(OUT / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')
subprocess.run([sys.executable, 'scripts/generate_part3_reports.py'], cwd=ROOT, check=True)
sys.exit(1 if failed else 0)
