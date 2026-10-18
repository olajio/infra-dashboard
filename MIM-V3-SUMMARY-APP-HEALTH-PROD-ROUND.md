# MIM V3 — summary: Application Health follows the CI, production only, Short description, Changes moved (16 Oct 2026)

All done and pushed to main (commit `ba91398`). To pick it up: import `MIM V3.ndjson` with overwrite, then
**More → Reset changes** and reload. Details: *MIM-V3-APP-HEALTH-BY-CI-AND-PROD-ONLY.md*.

## Your question

Before this change, *Application Health* used neither the Incident control nor the CI control. It always listed every
production application from the last hour. The Application control only filtered *Services of the Application*.

## Application Health now follows the selected CI

With an incident picked (or a CI chosen in the CI control) it lists only the applications related to that CI:
- business applications linked to it in the CMDB, in either direction (e.g. *Claim Center* for *Claim Center PROD*);
- applications whose services run on it, when the CI is a server;
- the CI itself, when it is a business application.

With nothing selected, it still lists every production application. Health still covers the last hour, even though
the panel shows a "Last 5 years" badge because it also reads the CMDB links. *Services of the Application* still
follows the Application control.

**Gap:** an application linked to the CI only through an application service, two steps away in the CMDB, is not
included unless its services run on the CI.

## Production only

Any environment starting with "prod" or "prd" counts as production (Production, Prod, prd1 and so on). Applied to:
- the related-CI tables and *Blast radius*;
- *Applications on this CI*;
- *Open Alerts with No Incident*.

Section 3 was already production only.

## Other changes

- **Short description** is back as the last column of *Active Incidents*.
- **Changes in the Last 7 Days on this CI** now sits right after *Escalate*.

## Checks

- All eleven tests pass on 9.5.3, and *Application Health*'s click-through to ServiceNow still works.
- Checked in Kibana 9.5.3 with *Claim Center PROD* selected: *Application Health* shows only *Claim Center*.
- The guide and walkthrough are updated.

## Two choices for you on the production filter

- **Items with no environment recorded are kept** and shown as "—". Many CMDB items have none (IP addresses, disks,
  network gear), and hiding them would bring back the blind spots fixed earlier. Say if you would rather hide them
  too.
- **The incident or CI you pick is never hidden,** whatever its environment. *Escalate*, *Alerts on this CI*, the
  health panels and *Changes* are not filtered, because they describe the CI you chose. Its *Env* column in
  *Escalate* tells you if it is not production.
