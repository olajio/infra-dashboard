// Run inside the Kibana container: uses Kibana's own getQuerySummary to tell real fields from columns created at query time.
const { getQuerySummary } = require('/usr/share/kibana/node_modules/@kbn/esql-utils/src/utils/get_query_summary.js');
const panels = require('/tmp/linkpanels.json');
let bad = 0;
for (const p of panels) {
  const s = getQuerySummary(p.query);
  const created = new Set([...s.newColumns, ...[...s.renamedColumnsPairs].map((x) => x[1])]);
  console.log(p.title + ': ' + p.cols.map((c) => `${c}=${created.has(c) ? 'COMPUTED (link blocked in 9.5)' : 'field (link OK)'}`).join(', '));
  bad += p.cols.filter((c) => created.has(c)).length;
}
console.log(bad ? `${bad} LINK COLUMN(S) ARE COMPUTED` : 'ALL LINK COLUMNS ARE REAL FIELDS');
