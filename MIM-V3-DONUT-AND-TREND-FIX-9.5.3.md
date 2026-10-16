# MIM V3 — donut and Time to Resolve fixes, verified on Kibana 9.5.3 (16 Oct 2026)

Reported with `bad_donut.png`. Both are fixed and pushed to main. To see the changes on the cluster: import
`MIM V3.ndjson` (overwrite), then **More → Reset changes** and reload.

## The donut: the real cause

My earlier hidden-slice fix was not what your screenshot showed: your legend itself said "P2 0".

- **Kibana 9.5 applies the dashboard's time range to the donut's query automatically.** Kibana 9.4, which I had been
  testing on, does not. I found it by reading 9.5.3's Vega code.
- **Your dashboard was on Last 24 hours,** so the donut only counted incidents whose record changed in the last 24
  hours. Your P2s had been On Hold for days without updates.
- **The table has its own fixed range of Last 1 month,** so it still listed them.

I reproduced your screenshot exactly on a real Kibana 9.5.3: P2 0 next to a table of On Hold P2s.

![Before, on 9.5.3: the donut reads P2 0 while the table lists three P2s](mim-v3-953-before.png)

**The fix:** the donut now has the same fixed "Last 1 month" range as the table, shown as a badge by its title. Both
count the same incidents whatever the time picker says. On 9.5.3 the donut reads P1 1, P2 3, P3 4, matching the table.

I also checked the **Incident control** on 9.5.3: it is not affected, and lists incidents not updated in the last
24 hours.

## Time to Resolve now starts at 0 h

- The log axis could not show values under 1 h, which is why lines were cut off. **Both axes now start at 0 h.**
- **P1 and P2** share the left axis with their 4 h and 8 h targets. **P3** has its own right axis, also from 0 h, with
  its 24 h target. On a single axis, P3's day-plus values would flatten P1 and P2 again.
- The axis titles and the legend ("P3 (right axis)") say which side is which.
- **Limit:** a P2 left open for many days stretches the left axis while it is open, because open incidents count with
  their age so far.

![After, on 9.5.3: the donut matches the table; Time to Resolve from 0 h](mim-v3-953-after.png)

## Testing is now on your version

- I set up Elasticsearch and Kibana **9.5.3** locally.
- All tests pass on it, and the link check confirms every clickable column works on 9.5.3. Until now everything had
  only been checked on 9.4.

## Decision for you

The donut and the table both count only incidents whose record was updated in the last month. An incident left On
Hold with no update for over a month would be missing from both. If that happens at CNA, I can widen the range.

More detail: part 5 of *MIM-V3-TIME-TO-RESOLVE-AND-DONUT.md*, which also corrects my earlier explanation.
