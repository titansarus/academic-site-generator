Scheduling looks simple: put work on machines. In practice, the objectives
conflict, the inputs are uncertain, and the scale is enormous.

## Three sources of difficulty

1. **Conflicting objectives** — latency, throughput, and fairness pull apart.
2. **Uncertainty** — job durations are rarely known in advance.
3. **Scale** — decisions must be made in microseconds across thousands of nodes.

A useful mental model is to separate *placement* from *ordering*, then reason
about each independently before combining them.
