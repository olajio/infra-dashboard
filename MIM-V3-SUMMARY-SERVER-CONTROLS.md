# MIM V3 — summary: CI / Server / Middleware / Database controls and automatic server health (18 Oct 2026)

Nothing has been built. Full assessment: *MIM-V3-SERVER-CONTROLS-FEASIBILITY.md*. Also saved: the previous answer, in
*MIM-V3-SERVICES-AND-SECTION2-CONDITIONS.md*.

**Yes, all of it is possible, with one exception on the time window.**

## 1. CI control listing every monitored CI: yes, a small change

It would list CIs on P1–P3 incidents plus every CI that sent monitoring data in the last day; you search it by
typing. A Kibana control holds at most 10,000 values, so the count query in the feasibility file should be run first.

## 2. Server control with your precedence: yes

The health panels would pick their server in this order:
1. the Incident's CI, if it is a server;
2. the CI control's value, if it is a server;
3. the Server control's value;
4. otherwise, the CI's servers from the CMDB (the automatic mode in point 4).

"Is a server" would mean "sends server metrics". That is the same data the panels show, so it always matches what can
be displayed.

Which panels follow the server:
- the six health panels;
- *Errors from the Logs* and *Alerts on this CI* too, since both are reported per server;
- *Escalate*, *Changes* and the related-CI tables stay on the incident's CI.

To test when building: whether the Server control's list can shrink to only the selected CI's servers. Kibana 9.5
appears to support it, but it is not certain the list refreshes when only the CI changes. If it does not, you would
search the full server list.

## 3. Middleware and Database controls: possible, but better left out for now

- **No reliable link.** The CMDB names middleware and databases one way (e.g. `Tomcat@vslrau1p276:8081`), and the
  monitoring data another (server plus process type).
- **What would work:** controls listing the monitored components, narrowing the Middleware, Database and Process
  Health tables. But those tables already list every component on the server, Down first, so the gain is small.
- **When they would help:** only if automatic mode shows long lists.

## 4. Automatic server health for an application CI: yes, but the time rule cannot work as written

A panel's time range is fixed in its settings; it cannot switch between "fixed 24 hours" and "time picker" depending
on a control. Two ways around it:
- **(a) Dashboard only, possible now.** These panels never follow the time picker, whether the server is automatic or
  picked. They use a fixed window (e.g. 24 hours), or a new "Health window" control (15 min / 1 h / 24 h / 7 days)
  that replaces the time picker for them.
- **(b) With a one-off cluster setup, recommended long term.** A lookup copy of the CMDB application-to-server links.
  The time picker does not apply to that lookup, so the panels follow the time picker in both modes and no fixed
  window is needed. It needs an index, a daily refresh job, someone to own it, and read access for viewers.

In both cases:
- *Server Health* would become one row per server (worst first) instead of four tiles.
- Each panel would get a Server column, so you can see which servers were picked automatically.
- One step in the CMDB covers application services like *Automated Claim Transaction PROD*. A business application
  usually needs two steps (business application → its services → their servers), which both designs can do.

## Suggestion

- **Phase 1:** the CI control lists every monitored CI, plus the Server control with the precedence above, keeping the
  time picker. Dashboard only.
- **Phase 2:** automatic servers, either (a) now or (b) once the lookup index has an owner.

## Decisions asked

1. Go ahead with phase 1?
2. For automatic servers: (a) now, with a fixed 24 hours or a "Health window" control, or (b) later, with the lookup
   index and the time picker?
3. Middleware and Database controls: leave out for now, or build the monitored-component version?
