# Use Step Lifecycle as the Executable Target seam

Step Lifecycle is the single seam for a Step from lifecycle decisions through StepResult recording. Request Step, Invoke Step, and Sleep Step stay as Executable Target implementations behind that seam, so repeat, skip, hook metadata, failfast, naming, and StepResult shape remain local to Step Lifecycle instead of being reimplemented in Runner.

**Status**: accepted

**Consequences**

- New Executable Target behaviour should enter through Step Lifecycle unless there is a strong reason to create a separate seam.
- Runner should orchestrate Case execution and not own per-Step lifecycle rules.
- Tests for repeat, skip, and StepResult behaviour should prefer the Step Lifecycle seam.
