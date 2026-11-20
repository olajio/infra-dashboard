**Subject:** Request: additional ServiceNow data to be ingested into Elastic for the MIM dashboard

Hi ATOS team,

We're building the next release of the Major Incident Management (MIM) dashboard in Kibana, and it needs some ServiceNow data that isn't in Elastic today. Could you please add the following to the ServiceNow integration?

1. **Critical outage record data**: the outage records linked to major incidents.
2. **Critical start time field**: when the outage or critical impact started.
3. **Critical Impact Mitigated field**: when the impact was mitigated.
4. **P1 Duration field**: the P1 duration as recorded in ServiceNow.
5. **PBA related field**: the field that flags incidents affecting business-critical (PBA) services.
6. **Managed-P2 (mp2) incident documents**: Managed-P2 incidents, which aren't in the index today.

With this data we can:

- Report P1 MTTR using the MIM team's adjustments from the outage record.
- Flag business-critical incidents.
- Include Managed-P2 incidents on the dashboard.

Could you let us know:

- Whether these fields and records are available to you on the ServiceNow side.
- Which Elastic indices and field names they would land in, so we can map them on the dashboard.
- A rough timeline for the change.

We're happy to set up a call to go through the details.

Thank you,
[Your name]
[Team / role]
