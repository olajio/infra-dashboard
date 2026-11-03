# MIM V4: how the application controls work

*3 Nov 2026. Applies to MIM V4 and the Infrastructure Dashboard (patch 03w).*

**Decision needed from the team:** should the section 3 **Application** list follow the application picked in the top
**Monitored application** control? Kibana 9.5.3 supports this (tested on 3 Nov). See the question at the end.

## The controls involved

| Control | Where | What it offers |
|---|---|---|
| **Monitored application** | Top bar, under Incident and CI | The applications MIM escalates: every application in `cmdb_with_apm_flag` that is **In Production**, **Operational** and **monitored** (138 on 2 Nov). Default: *(all monitored applications)* |
| **Application** | Section 3, second control | The applications from that same monitored set **that sent APM data in the last 24 hours**. Default: *(all applications)* |
| **Service** | Section 3, third control | The services of those applications. Default: *(services on this CI)* |

The rules (In Production, Operational, monitored) come from `cmdb_with_apm_flag`, which is filled from ServiceNow.
APM data is matched to an application on its APM number, so an application's name can differ slightly between the
top control (CMDB name) and section 3 (name in the APM data).

## Two separate things: the rules, and your pick

The section 3 Application list follows the **rules** of the monitored set. It does **not** follow **the value you
pick** in the top control.

- **The rules:** the section 3 list runs its own query with the same three conditions. It can only ever offer
  applications from the monitored set.
- **Your pick:** choosing one application in the top control does not narrow the section 3 list. It keeps offering
  every monitored application with APM data.

### Example

Three applications:

| Application | In Production, Operational, monitored? | Sends APM data? |
|---|---|---|
| Juno | Yes | Yes |
| Claim Center | Yes | Yes |
| Payment Hub | No (not monitored) | Yes |

| Top control: Monitored application | Section 3 Application list offers | Why |
|---|---|---|
| *(all monitored applications)* | Juno, Claim Center | Payment Hub fails the rules |
| **Juno** | Juno, Claim Center | The list ignores the top pick |

Payment Hub never appears, whatever is picked: that is the list following the rules. Claim Center stays in the list
after Juno is picked: the list does not follow the pick.

## What the panels show

The panels apply **both** controls.

| Panel | Follows the top control | Follows the section 3 Application control |
|---|---|---|
| *Application Health* | Yes: the monitored set, or the one picked | No |
| *Services of the Application* | Yes | Yes |
| Section 3 *Application* and *Service* lists | Rules only, not the pick | — |
| *Service health*, *Upstream*, *Downstream* | Through the Service picked | Through the Service picked |
| Sections 1 and 2 (incidents, CMDB) | No | No |

**Watch out:** picking *different* applications in the two controls empties *Services of the Application*. For example:
top control = Juno, section 3 Application = Claim Center. No service belongs to both, so the panel shows nothing.
Set either control back to its "(all …)" value to see services again.

## The lists are dynamic

No application names are stored in the dashboard. Each list is a query that runs when the dashboard loads.

- **A newly monitored application** appears in the top control on the next load after `cmdb_with_apm_flag` is
  refreshed from ServiceNow. One that is retired, or no longer monitored, disappears the same way.
- **In section 3**, it appears once its services send APM data. Until then, *Application Health* lists it as
  *Enrolled — no telemetry yet*.
- **The dashboard's time range does not affect the lists** (tested on 3 Nov).

## Kibana supports making the section 3 list follow the top pick

Tested on Kibana 9.5.3 on 3 Nov. A test dashboard had a top-bar control and a control inside a section whose list
query read the top-bar control's value:

| Top control | Section control's list |
|---|---|
| a | apple, avocado |
| b | banana, blueberry |

The section control's list changed as soon as the top value changed.

**One behaviour to know:** when the top pick changes, the section control **keeps its previous selection**, even if
that value is no longer in its list. Kibana marks it with a warning icon as an "incompatible selection", and it stays
until someone picks again. On MIM V4:

1. Pick *Juno* in the section 3 Application control.
2. Change the top control to *Claim Center*.
3. Section 3 still holds *Juno*, with a warning, and *Services of the Application* is empty until someone picks
   *Claim Center* or *(all applications)* in section 3.

*(all applications)* would always stay in the section 3 list, so there is always a quick way back.

## Question for the team

Should the section 3 Application list follow the application picked in the top **Monitored application** control?

| Option | What changes | Trade-off |
|---|---|---|
| **A. Follow the top pick** | Picking Juno at the top leaves only Juno (and *(all applications)*) in the section 3 list | Fewer wrong combinations; but a stale section 3 pick stays, with a warning, after the top pick changes |
| **B. Leave as is** | Nothing | Simple; but two different picks can empty *Services of the Application* |

Reply with A or B.
