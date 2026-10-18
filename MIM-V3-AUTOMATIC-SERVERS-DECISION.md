# MIM V3 — automatic servers: what the Round 11 numbers say (18 Oct 2026)

*Assessment and proposal only: nothing has been built.* The numbers come from `round11.txt`. The queries and a
results table are in `queries_ro_run.md` (Round 11).

## Short answer

**Full automatic mode (option A) is not possible on this cluster.** Every automatic panel has to read every server's
data in the Health window, and the data is too big:

| Panel | 1 hour | 24 hours |
|---|---|---|
| Server Health (CPU, memory, disk; 17.7 M documents a day) | 1.4 s, 10 CPU-seconds | **8.9 s, 582 CPU-seconds** |
| Middleware / Database / Process Health (processes 202 M a day, Windows services 43 M) | 4.2 s, 166 CPU-seconds | **timed out** (502) |
| Errors from the Logs (1.1 billion log lines a day) | **timed out** (502) | — |

- **The dashboard refreshes every 5 minutes.** At 24 hours, Server Health alone would cost the cluster about 10
  CPU-minutes per viewer per refresh, and 3 or 7 days would cost 3 to 7 times more. Logs and processes cannot run at
  all.
- **Option B (automatic Server Health only) is too heavy too**, except for windows of an hour or less.
- **Phase 1 is not affected.** When a server is known, Elasticsearch filters on its name first. The Round 11b
  queries BJ–BL confirm this on real data.

## Why it still matters

**Half of the incidents are on a CI that is not a server.** 867 of the 1,725 CIs with a P1–P3 in the last 31 days
send no server metrics: application services, business applications, network devices. For those, you have to read a
server name in *Server View* and pick it in the Server control.

**An application can have many servers.** *Claim Center PROD* links to about 160 servers in the CMDB. Even if it were
fast, automatic mode on every panel would list 160 servers' processes and log errors, which is too much to read
during an incident.

## Proposal: live status in Server View (the cheap automatic part)

*Server View* already lists the selected CI's servers from the CMDB, in both directions. It would get three new
columns:

| Column | Meaning |
|---|---|
| **Status** | *Reporting* (green): CPU data in the last 15 minutes. *No data 15 min* (red): down, agent stopped, or not monitored |
| **Min. ago** | Minutes since the server's last CPU data |
| **CPU now** | Highest CPU in the last 15 minutes, green / amber (≥ 80 %) / red (≥ 90 %) |

**How you'd use it:**
1. Pick an incident on an application.
2. *Server View* shows at a glance which of its servers are silent or running hot.
3. Type that server into the Server control. The other health panels then show it in depth, over the Health window.

**Cost:** one scan of CPU data only, over a fixed 15 minutes. That is about 1/12 of BE's 1-hour figure, so roughly a
tenth of a second, and it is the same whatever the Health window. **BM** in Round 11b measures it.

**Limits:**
- **A silent server and an unmonitored server look the same** ("No data 15 min"). Telling them apart needs a longer
  window, which is what makes automatic mode expensive.
- **The 15 minutes are fixed**, not the Health window. Status is about *now*. The Server control gives the history.
- **A business application** usually reaches its servers through its services (two CMDB steps), so its own *Server
  View* is often empty. Pick one of its services instead. BH2 checks whether APM can fill that gap.

## Choices

| | What | Cost |
|---|---|---|
| **E (recommended)** | Live status in *Server View*, plus the Server control for depth | About 0.1 s per refresh |
| **C** | Keep phase 1 as it is | None |
| **B, limited** | Automatic *Server Health* with a 1-hour cap, whatever the Health window | About 1.5 s and 10 CPU-seconds per refresh, and the cap contradicts the Health window |
| **A** | Automatic mode on every panel | Not possible: times out |

## Before deciding

Run **Round 11b** in `queries_ro_run.md`, all in Dev Tools:

| Query | What it checks |
|---|---|
| **BH2** | The fixed APM query: does APM find a business application's servers? |
| **BJ–BL** | Phase 1's own Server, Process and Logs panels on real data, at 24 hours and 7 days |
| **BM** | What option E costs |
