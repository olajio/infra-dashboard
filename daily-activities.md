# Daily activities

## 17 Nov 2026

**MIM V5**
1. Removed P3 incidents from the dashboard entirely, leaving P1 and P2. P2s still appear once they're past their 8 h
   target. This covered the tiles, *Needs attention now*, *Active Incidents*, *Escalation Channel*, the Incident and CI
   dropdowns, and the time-to-resolve chart.
2. Narrowed the *Active Incidents* table by about 25 % and widened the *P1 / P2 Time to Resolve vs Target* chart to fill
   the space.
3. Reviewed the zigzag in the P3 line on the time-to-resolve chart. Each point is the median of only the incidents
   resolved that day, so values jump from day to day. A rolling 7-day median was offered as a smoother alternative.
4. Ran the follow-up ServiceNow checks:
   - **PBA:** no PBA field exists in the data.
   - **Duration fields:** not on the incident records. They sit in another ServiceNow index, which the R4e/R4f queries
     will identify.
5. Updated the MIM V5 user manual and seven rows of the MIM KPI spreadsheet for the P3 removal.

**Infrastructure Overview**
1. Adopted the team's updated version (*Infrastructure Overview v2*) as the new basis.
2. Rebuilt the Dashboard Links section into two subsections:
   - **Related Dashboards:** Executive (in progress), Portfolio, Applications Operations, Major Incident Management.
   - **Detailed Dashboards:** Cloud Infra, Database Infra, Middleware, Server Infra, VMware Infra.
3. Added a Future Releases section with *Next Release Roadmap* and *Predictive & AI Insights* cards, listing the planned
   infrastructure items.
4. Updated the user manual.

**Open from today**
- Run the R4e/R4f queries to find where the P2 duration is held.
- Decide whether the time-to-resolve chart should use a rolling 7-day median.
