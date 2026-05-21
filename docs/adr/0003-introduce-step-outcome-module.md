# Introduce Step Outcome Module for Request Step response handling

Step Outcome is the deep Module for Request Step response handling after an HTTP response is received and before StepResult is recorded. Step Lifecycle keeps lifecycle timing, repeat, skip, hooks, failfast, and StepResult ordering; Step Outcome owns validate, extract, persist, export, response.save_body_to, and report-safe response shaping.

**Status**: accepted

**Consequences**

- Response Capture remains a separate Module and is called by Step Outcome.
- Export CSV failure keeps current Request Step behaviour instead of being silently downgraded.
- The first implementation covers Request Step only; Sleep Step and Invoke Step do not enter Step Outcome.
