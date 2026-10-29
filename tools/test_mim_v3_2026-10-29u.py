"""Check the 29 Oct round: Application Health lists enrolled applications with no telemetry yet, and the Telemetry
control; the rows for applications with APM data are unchanged.

Usage: test_mim_v3_2026-10-29u.py OLD_MIM_V3_NDJSON NEW_MIM_V3_NDJSON
(OLD = before mim_v3_patch_2026-10-29u.py, for the unchanged-rows check; local Elasticsearch on port 9200. Creates
`cmdb_with_apm_flag` locally and removes it, with test -15's APM data, at the end.)
"""
import json
import sys
import urllib.request

HERE = __file__.rsplit('/', 1)[0]
ES = 'http://localhost:9200'
FLAG = 'cmdb_with_apm_flag'
LABEL = 'Enrolled — no telemetry yet'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def cleanup():
    for ds in (call('GET', '/_data_stream/*-test*').get('data_streams') or []):
        call('DELETE', f'/_data_stream/{ds["name"]}')
    call('DELETE', '/_index_template/apm-tx-test')
    call('DELETE', f'/{FLAG}')


cleanup()
src = open(f'{HERE}/test_mim_v3_2026-10-15.py').read().split('dash = json.loads')[0]   # test -15's APM data
exec(compile(src, 'test_mim_v3_2026-10-15.py', 'exec'), {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v3_2026-10-15.py'})

T = {'type': 'text', 'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}}}
call('PUT', f'/{FLAG}', {'mappings': {'properties': {   # as in round18.txt OB1
    '@timestamp': {'type': 'date'}, 'name': T, 'number': T, 'install_status': T, 'is_monitored': {'type': 'boolean'},
    'support_group': {'properties': {'l2': {'properties': {'name': T}}}}, 'customer_specific': {'properties': {'pm_portfolio': T}}}}})
app = lambda name, number, enrolled, status='Installed': {
    '@timestamp': '2026-10-29T14:12:30Z', 'name': name, 'number': number, 'is_monitored': enrolled,
    'install_status': status, 'support_group': {'l2': {'name': 'IT.' + name[:3]}}}
docs = [app('Juno', 'APM-Jun', True),                 # sends APM data: shown as today, not as a silent one
        app('Silent App', 'APM-SIL', True),           # enrolled, no APM data: the new row
        app('Gone App', 'APM-GON', True, 'Retired'),  # retired: left out
        app('Plain App', 'APM-PLA', False)]           # not enrolled: left out
assert not call('POST', '/_bulk?refresh=true',
                ''.join(json.dumps({'index': {'_index': FLAG}}) + '\n' + json.dumps(d) + '\n' for d in docs), nd=True).get('errors')

load = lambda f: {(p['embeddableConfig'].get('title') or ''): p for p in json.loads(json.loads(open(f).readline())['attributes']['panelsJSON'])}
OLD, NEW = load(sys.argv[1]), load(sys.argv[2])
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def health(panels, ci='(no CI selected)', telemetry=None):
    ec = panels['Application Health']['embeddableConfig']
    params = [{'incident': '(all incidents)'}, {'ci': ci}] + ([{'telemetry': telemetry}] if telemetry else [])
    r = call('POST', '/_query?format=json', {'query': ec['attributes']['state']['query']['esql'], 'params': params,
                                             'filter': {'range': {'@timestamp': {'gte': 'now-5y', 'lte': 'now'}}}})
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


try:
    print('Application Health, Telemetry = (all applications)')
    rows = health(NEW, telemetry='(all applications)')
    old = health(OLD)
    check('rows with APM data unchanged', [r for r in rows if r['app_health'] != LABEL], old)
    silent = [r for r in rows if r['app_health'] == LABEL]
    check('the enrolled application with no telemetry, after the others', (rows[-1]['ci.name'], len(silent)), ('Silent App', 1))
    check('its row', {k: silent[0][k] for k in ('services', 'tx', 'app_number', 'app_support', 'servers')},
          {'services': 0, 'tx': 0, 'app_number': 'APM-SIL', 'app_support': 'IT.Sil', 'servers': '—'})
    check('retired, not enrolled and sending applications not listed as silent',
          sorted({r['ci.name'] for r in silent} & {'Gone App', 'Plain App', 'Juno'}), [])
    check('with a CI picked: no silent applications', [r['ci.name'] for r in health(NEW, ci='Juno', telemetry='(all applications)')], ['Juno'])
    print('Application Health, Telemetry = Enrolled, no telemetry yet')
    check('only the worklist', [r['ci.name'] for r in health(NEW, telemetry='Enrolled, no telemetry yet')], ['Silent App'])
    check('whatever the CI', [r['ci.name'] for r in health(NEW, ci='Juno', telemetry='Enrolled, no telemetry yet')], ['Silent App'])
    print('Telemetry control')
    ctl = NEW['Telemetry']['embeddableConfig']
    r = call('POST', '/_query?format=json', {'query': ctl['esql_query']})
    check('values', [v[0] for v in r['values']], ['(all applications)', 'Enrolled, no telemetry yet'])
    check('default and variable', (ctl['selected_options'], ctl['variable_name']), (['(all applications)'], 'telemetry'))
    row = sorted((p for p in NEW.values() if p['type'] == 'esql_control'), key=lambda p: p['gridData']['x'])
    check('section 3 control row', [(p['embeddableConfig']['title'], p['gridData']['x'], p['gridData']['w']) for p in row],
          [('Server', 0, 10), ('Health window', 10, 8), ('Service', 18, 10), ('Application', 28, 10), ('Telemetry', 38, 10)])
    colours = {a['rules'][0]['pattern'] for c in NEW['Application Health']['embeddableConfig']['attributes']['state']['visualization']['columns']
               if c['columnId'] == 'app_health' for a in c['colorMapping']['assignments']}
    check('badge colour for the new status', LABEL in colours, True)
finally:
    cleanup()

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
