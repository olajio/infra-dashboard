"""Build MIM V5 (3 Nov 2026): MIM V4 with a new look, nothing removed. Every query of MIM V4 is kept as it is.

Usage: build_mim_v5.py "MIM V4.ndjson" "MIM V5.ndjson"

Borrowed from the Portfolio and Applications Operations dashboards, which the team likes:
- Section 1 opens with KPI tiles in the Portfolio style: an icon, a big number coloured by state, and a priority
  strip. Two new tiles: "Needs attention now" (P1 + P2 over 8 h + P3 over 24 h, with the strip) and "Open alerts, no
  incident" (bell, with a severity strip). The three existing tiles (Active P1, P2 over 8 h, P3 over 24 h) get a
  priority badge and "All clear" / "Needs action" text; their queries are unchanged.
- "Zero is calm": numbers are green at 0 and take the priority colour above 0 (war-room practice).
- Section titles carry an icon; the two placeholder tiles (User base, RUM) are smaller, beside Time to Resolve.
- Long tables show row numbers, as in the Portfolio tables.
MIM V5 has its own id, so importing it leaves MIM V4 in place.
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
NS = 'mim-dashboard/v5/'
uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, NS + name))
RED, AMBER, BLUE, GREEN = '#d6453d', '#c98a0b', '#3f6fb5', '#1f9e6b'   # MIM V4's priority palette (badges, TTR lines)

lines = [json.loads(l) for l in open(SRC) if l.strip()]
v4 = next(o for o in lines if o.get('type') == 'dashboard')
dash = copy.deepcopy(v4)
dash['id'] = uid('dashboard')
A = dash['attributes']
A['title'] = 'MIM V5'
A['description'] = ('Major Incident Management, V5: the same panels and controls as MIM V4 with a new look (KPI tiles '
                    'with icons and priority strips, section icons). ' + v4['attributes'].get('description', ''))
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
S1 = P['Active P1']['gridData']['sectionId']

# ------------------------------------------------------------------ helpers
def vega_panel(name, spec, x, y, w, h, description, time_range, section=S1):
    pid = uid('panel/' + name)
    return {'type': 'legacy_vis', 'panelIndex': pid,
            'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section},
            'embeddableConfig': {'savedVis': {'title': name, 'description': '', 'type': 'vega',
                                              'params': {'spec': json.dumps(spec, indent=2)}, 'uiState': {},
                                              'data': {'aggs': [], 'searchSource': {}}},
                                 'title': name, 'hide_title': True, 'description': description,
                                 'time_range': dict(time_range)}}


def text(x, y, value=None, signal=None, size=13, weight='normal', fill=None, style=None, align='left',
         baseline='alphabetic', opacity=None, limit=None):
    enc = {'x': x, 'y': y, 'fontSize': {'value': size}, 'fontWeight': {'value': weight},
           'align': {'value': align}, 'baseline': {'value': baseline}}
    enc['text'] = {'signal': signal} if signal else {'value': value}
    if fill:
        enc['fill'] = {'signal': fill} if fill.startswith('(') or '?' in fill else {'value': fill}
    if opacity is not None:
        enc['opacity'] = {'value': opacity}
    if limit:
        enc['limit'] = {'signal': limit}
    m = {'type': 'text', 'encode': {'update': enc}}
    if style:
        m['style'] = style
    return m


def badge(cx, cy, colour, label, r=19, shape='circle'):
    """Icon: a tinted disc (or triangle) with a label, like the Portfolio's incident and alert tiles."""
    size = 3.1416 * r * r if shape == 'circle' else 2.6 * r * r
    return [
        {'type': 'symbol', 'encode': {'update': {'x': {'value': cx}, 'y': {'value': cy}, 'shape': {'value': shape},
                                                 'size': {'value': size}, 'fill': {'value': colour},
                                                 'fillOpacity': {'value': 0.18}, 'stroke': {'value': colour},
                                                 'strokeWidth': {'value': 1.5}}}},
        text({'value': cx}, {'value': cy + (1 if shape == 'circle' else 5)}, value=label,
             size=15 if len(label) <= 2 else 18, weight='bold', fill=colour, align='center', baseline='middle'),
    ]


def esql_data(query):
    return [{'name': 'raw', 'url': {'%type%': 'esql', 'query': query}}]


def first(col):
    return f"length(data('raw')) ? (data('raw')[0].{col} || 0) : 0"


def tile_spec(query, title_text, subtitle, colour, label):
    """The three existing tiles, restyled: badge, title, subtitle, state text, big number. Query unchanged."""
    return {
        '$schema': 'https://vega.github.io/schema/vega/v5.json',
        'autosize': {'type': 'fit', 'contains': 'padding'}, 'padding': 0,
        'data': esql_data(query),
        'signals': [{'name': 'n', 'update': first('incidents')}],
        'marks': badge(30, 32, colour, label) + [
            text({'value': 58}, {'value': 26}, title_text, size=14, weight='bold', style='guide-label',
                 limit='width - 70'),
            text({'value': 58}, {'value': 43}, subtitle, size=11, style='guide-label', opacity=0.7, limit='width - 70'),
            text({'value': 12}, {'signal': 'height - 10'}, signal="n > 0 ? 'Needs action' : 'All clear'", size=12,
                 weight='bold', fill=f"(n > 0 ? '{colour}' : '{GREEN}')"),
            text({'signal': 'width - 12'}, {'signal': 'height - 6'}, signal='n', size=38, weight='bold',
                 fill=f"(n > 0 ? '{colour}' : '{GREEN}')", align='right'),
        ],
    }


def strip_spec(query, cols, title_text, subtitle, label, shape, icon_colour, total_label):
    """New hero tiles: icon, big total coloured by the worst non-zero part, and a stacked strip with a legend."""
    sig = [{'name': c, 'update': first(c)} for c, _, _ in cols]
    total = ' + '.join(c for c, _, _ in cols)
    worst = ' : '.join(f"{c} > 0 ? '{col}'" for c, _, col in cols) + f" : '{GREEN}'"
    sig += [{'name': 'total', 'update': total}, {'name': 'worst', 'update': worst},
            {'name': 'barX', 'value': 14}, {'name': 'barW', 'update': 'max(width - 28, 10)'}]
    marks = badge(32, 34, icon_colour, label, r=20, shape=shape) + [
        text({'value': 62}, {'value': 26}, title_text, size=14, weight='bold', style='guide-label', limit='width - 150'),
        text({'value': 62}, {'value': 43}, subtitle, size=11, style='guide-label', opacity=0.7, limit='width - 150'),
        text({'signal': 'width - 14'}, {'value': 50}, signal='total', size=40, weight='bold', fill='(worst)',
             align='right'),
        text({'signal': 'width - 14'}, {'value': 64}, total_label, size=10, style='guide-label', opacity=0.7,
             align='right'),
        {'type': 'rect', 'encode': {'update': {'x': {'signal': 'barX'}, 'y': {'signal': 'height - 36'},
                                               'width': {'signal': 'barW'}, 'height': {'value': 10},
                                               'fill': {'value': '#8a96a8'}, 'fillOpacity': {'value': 0.22},
                                               'cornerRadius': {'value': 3}}}},
    ]
    left = 'barX'
    for i, (c, name, col) in enumerate(cols):
        marks.append({'type': 'rect', 'encode': {'update': {
            'x': {'signal': left}, 'y': {'signal': 'height - 36'}, 'height': {'value': 10},
            'width': {'signal': f'total > 0 ? {c} / total * barW : 0'}, 'fill': {'value': col},
            'tooltip': {'signal': f"{{'{name}': {c}}}"}}}})
        left = f'{left} + (total > 0 ? {c} / total * barW : 0)'
        marks.append(text({'signal': f'barX + {i} * barW / {len(cols)}'}, {'signal': 'height - 10'},
                          signal=f"'{name}  ' + {c}", size=12, weight='bold', fill=col))
    return {'$schema': 'https://vega.github.io/schema/vega/v5.json',
            'autosize': {'type': 'fit', 'contains': 'padding'}, 'padding': 0,
            'data': esql_data(query), 'signals': sig, 'marks': marks}


# ------------------------------------------------------------------ section 1: KPI tiles
spec_of = lambda t: json.loads(P[t]['embeddableConfig']['savedVis']['params']['spec'])
q1 = spec_of('Active P1')['data'][0]['url']['query']
BASE = q1[:q1.index('| WHERE pri == 1')]
for t, sub, colour, label in (('Active P1', 'any age', RED, 'P1'), ('P2 over 8 h', 'open longer than the 8 h target', AMBER, 'P2'),
                              ('P3 over 24 h', 'open longer than the 24 h target', BLUE, 'P3')):
    sv = P[t]['embeddableConfig']['savedVis']
    q = spec_of(t)['data'][0]['url']['query']
    assert q.startswith(BASE)
    sv['params']['spec'] = json.dumps(tile_spec(q, t, sub, colour, label), indent=2)
    P[t]['embeddableConfig']['hide_title'] = True

hero_q = BASE + ('| EVAL bucket = CASE(pri == 1, "p1", pri == 2 AND age_minutes > 480, "p2", pri == 3 AND age_minutes > 1440, "p3")\n'
                 '| STATS p1 = SUM(CASE(bucket == "p1", 1, 0)), p2 = SUM(CASE(bucket == "p2", 1, 0)), p3 = SUM(CASE(bucket == "p3", 1, 0))')
hero = vega_panel('Needs attention now', strip_spec(
    hero_q, [('p1', 'P1', RED), ('p2', 'P2 > 8 h', AMBER), ('p3', 'P3 > 24 h', BLUE)],
    'Needs attention now', 'P1 · P2 over 8 h · P3 over 24 h', '!', 'triangle-up', RED, 'incidents'),
    0, 0, 12, 7,
    'Active incidents past their target, in one number: every P1, P2s open longer than 8 h and P3s open longer than '
    '24 h. Green at 0. The strip splits it by priority; the same incidents as the Active Incidents table.',
    P['Active P1']['embeddableConfig']['time_range'])

oa = P['Open Alerts with No Incident']['embeddableConfig']
oq = oa['attributes']['state']['query']['esql']
head = '| WHERE _index LIKE "*netcool*" OR (state_name NOT IN ("Resolved", "Closed", "Canceled", "Cancelled") AND opened_at >= NOW() - 31 days)\n'
assert head in oq   # the table relies on its panel's 24 h range; the tile states it, so both count the same alerts
oq24 = oq.replace(head, '| WHERE @timestamp >= NOW() - 24 hours AND (_index LIKE "*netcool*" OR (state_name NOT IN ("Resolved", "Closed", '
                        '"Canceled", "Cancelled") AND opened_at >= NOW() - 31 days))\n')
alerts_q = oq24[:oq24.index('| SORT sev_rank DESC')] + (
    '| STATS critical = SUM(CASE(alert_severity == "Critical", 1, 0)), major = SUM(CASE(alert_severity == "Major", 1, 0)),\n'
    '        other = SUM(CASE(alert_severity IN ("Critical", "Major"), 0, 1))')
alerts = vega_panel('Open alerts, no incident', strip_spec(
    alerts_q, [('critical', 'Critical', RED), ('major', 'Major', AMBER), ('other', 'Other', BLUE)],
    'Open alerts, no incident', 'Netcool · CIs with no open incident', '🔔', 'circle', AMBER, 'alerts'),
    36, 0, 12, 7,
    'Open Netcool alerts on production CIs that have no open incident: possible blind spots. Same alerts as the Open '
    'Alerts with No Incident table, counted by severity.', oa.get('time_range') or {'from': 'now-24h', 'to': 'now'})

lay = {'Active P1': (12, 0, 8, 7), 'P2 over 8 h': (20, 0, 8, 7), 'P3 over 24 h': (28, 0, 8, 7),
       'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)': (0, 7, 36, 11),
       'User base · ServiceNow': (36, 7, 12, 5), 'Real users · RUM': (36, 12, 12, 6),
       'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)': (0, 18, 48, 12), 'Open Alerts with No Incident': (0, 30, 48, 11)}
for t, (x, y, w, h) in lay.items():
    P[t]['gridData'].update(x=x, y=y, w=w, h=h)
panels += [hero, alerts]

# ------------------------------------------------------------------ tables: row numbers on the long lists
for t in ('Active Incidents (P1 · P2 over 8 h · P3 over 24 h)', 'Open Alerts with No Incident', 'Errors from the Logs',
          'Services of the Application', 'Application Health'):
    P[t]['embeddableConfig']['attributes']['state']['visualization']['showRowNumbers'] = True

# ------------------------------------------------------------------ section titles with an icon
icons = {'1 · ': '🚨 ', '2 · ': '🔎 ', '3 · ': '🩺 ', '4 · ': '🔗 '}
for s in A['sections']:
    for k, ic in icons.items():
        if s['title'].startswith(k):
            s['title'] = ic + s['title']

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))
with open(OUT, 'w') as f:
    for o in [o for o in lines if o.get('type') != 'dashboard'] + [dash]:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: id {dash["id"]}, {len(panels)} panels (MIM V4 + 2 tiles); sections: ' + ' | '.join(s['title'] for s in A['sections']))
