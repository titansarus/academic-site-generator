## SchedSim

SchedSim is a discrete-event simulator for evaluating cluster scheduling
policies at scale. It supports pluggable policies, trace replay, and reporting.

### Features

- Trace-driven and synthetic workloads
- Pluggable scheduling policies
- Latency and utilization reporting

The core scheduling objective can be written as minimizing $\sum_i w_i C_i$,
the weighted sum of completion times.
