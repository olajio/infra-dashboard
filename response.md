# Status: P1 MTTR and P2 Duration (MIM)

**P1 MTTR and P2 Duration: built on MIM V5, now being checked on live data.**

As agreed with James and Dan, MIM reports P1 MTTR and P2 Duration instead of the ServiceNow SLAs.

## How they're measured

- **P1 MTTR:** from when the incident **became a P1** to resolved. While a P1 is open, it counts up to now. The P1 time
  comes from the ServiceNow incident timeline in Elastic, which records each priority change with its time. If the
  incident was opened as a P1, the opened time is used.
- **P2 Duration:** from **opened** to resolved, or to now while it's still open. It uses ServiceNow's
  `resolution_time` when that's filled in.

## Where they show on MIM V5

- The *Active Incidents* table has a **Time as P1 / Duration (h)** column for every open P1 and P2.
- The *Time to Resolve vs Target* chart has a **P1 MTTR line** and a **P2 Duration line**. Each is a rolling 7-day
  median, plotted against the 4 h and 8 h targets.
- A **Linked incidents** column shows how many incidents are linked to each P1, which indicates user impact.

**Example:** INC2692216 (Email/Exchange) became a P1 at 20:10 on 12 Nov and was resolved at 22:59 on 13 Nov. That's an
**MTTR of 26.8 h**. Its Duration from opening was 28.5 h.

## Still to do

- Import the updated MIM V5 and confirm the figures on live data.
- The MIM team's manual adjustments to the ServiceNow Outage record aren't included, because Outage records aren't sent
  to Elastic. If those adjustments need to count, the ServiceNow team would have to add the Outage table to the
  integration.
