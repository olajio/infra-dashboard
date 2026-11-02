**Subject:** Missing incident SLA records in Elastic (servicenow-task-sla)

Hi team,

We're building the MIM dashboard in Kibana, and its SLA column reads ServiceNow's SLA records from the `servicenow-task-sla` index. Most incidents have no SLA record in that index, so the dashboard shows "No SLA record" for them. Could you help us find out whether records are being missed by the integration?

**What we see in Elastic**
- `servicenow-task-sla` is an alias over a single index, `servicenow-task-sla-000001`, with about 200,600 records. Every record has `task_has_breached`, so the field itself is fine.
- Only **107 of the 3,224 incidents opened 20–26 Oct (3.3%)** have any SLA record, based on a 298-record export of the SLA records synced over those days.
- Of the **200 active P3 incidents** opened in the last 7 days, only **4** have an SLA record.
- The index grows by only about 20 records a day, while hundreds of incidents are opened daily. It also holds request (RITM) SLAs.
- The incident SLAs that do arrive all belong to specific contracts, such as the App Dev vendor SLAs, Atos, PAS Helpdesk and Security.

**Examples with no SLA record**, searched by `task_number` and by `task_sys_id`, with no time limit:

| Incident | sys_id | Priority | State |
|---|---|---|---|
| INC2677001 | a817622d3b481710c36cb78c24e45a67 | P3 | New |
| INC2676945 | aec242ad3b04db1087fb42d643e45a5d | P3 | In Progress |
| INC2677042 | 1e253ee52b48df10f841fb05ce91bfd7 | P3 | In Progress |

**Our questions**
1. Do these incidents have records in their **Task SLAs** related list in ServiceNow? If the list is empty, no SLA applies and the dashboard is right. If records are there, they're not reaching Elastic.
2. Which `task_sla` records does the integration select? For example, is it filtered by contract, task type, assignment group or update time?
3. If records are being missed, can the sync include every `task_sla` record whose task is an incident, and backfill the missing ones?
4. How often does the sync run, and are in-progress SLA records re-sent as their percentage and breach status change?

Happy to share the queries we used. Thanks for your help.

Regards,
[Your name]
