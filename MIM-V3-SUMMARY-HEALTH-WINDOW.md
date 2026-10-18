# MIM V3 — summary: fixed 24 hours and a "Health window" control (18 Oct 2026)

Nothing built at the time of this answer.

## Can a fixed 24 hours and a "Health window" control work together? Yes

The Health window would be a dropdown control with a **default of 24 hours**, so 24 hours is the normal behaviour
without anyone touching it:
- options such as 15 minutes, 1 hour, 6 hours, **24 hours (default)**, 3 days, 7 days;
- a longer option (3 or 7 days) widens the health panels when picked;
- the panels' queries read the chosen window directly, so Elasticsearch filters on it efficiently.

**Shorter windows.** As first asked, only a window *larger* than 24 hours would change anything. That is possible,
but I recommended letting shorter windows apply too: during an incident, "the last 15 minutes" or "the last hour" is
often the question, for example CPU in the last 15 minutes rather than over the day. Whether something is down *right
now* is not affected either way, because "Down" is always judged on the last 10 minutes.

To confirm on 9.5.3 before building:
- that a control with a fixed list of values works there;
- that the query can turn its value into a time window efficiently.

## Why a fixed 24 hours or a Health window instead of the time picker?

1. **The main reason is technical.** To find an application's servers automatically, the panels must read the CMDB
   relationship records.
   - Those records are only re-sent when the relationship changes: the oldest go back to 2023, and only about 129,000
     of 34 million change in a week.
   - Kibana applies a panel's time range to **every** index the panel reads, the CMDB records included.
   - If these panels followed the time picker (e.g. 24 hours), almost every CMDB link would be cut off, and automatic
     mode would find no servers.

   So these panels need a long fixed range for the CMDB records, with the health window applied inside the query to
   the monitoring data. That is what the Health window does in place of the time picker.
2. **Without automatic mode, the time picker would be fine.** If servers were only ever picked by hand (phase 1), the
   panels could keep the time picker. Likewise with option (b), a lookup copy of the CMDB links: lookups are not
   time-filtered, so the time picker would work in every mode.
3. **Side benefit:** the health panels stop depending on whatever the time picker was last set to. With "Last 15
   minutes", a server that went silent 30 minutes ago would show nothing; a 24-hour default always shows it, as Down.

## Consequences

- **The time picker would do very little.** Section 1 has fixed ranges, section 3 a fixed last hour, and the section
  2 health panels would follow the Health window.
- **Phase 1 should use the Health window too.** If automatic servers use a Health window, the panels phase 1 touches
  are the same ones. Building them once avoids redoing them.
- *Applications on this CI* (7 days) and *Alerts on this CI* (7 days) keep their own fixed windows, unless they should
  follow the Health window too.

## Questions asked

1. Should shorter windows apply, or only windows longer than 24 hours?
2. Build phase 1 and automatic servers together, all on the Health window (recommended)?
3. Middleware and Database controls: leave out for now?
