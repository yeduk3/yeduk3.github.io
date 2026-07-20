# Designing UI that explains itself

## Good interfaces reduce the need for extra explanation

The best product surfaces often feel simple because they make state transitions obvious. Users can tell when something is loading, what action matters most, and why the current screen looks the way it does.

A useful technical post gets stronger when it names the exact friction. Instead of saying "the UI feels messy," it is more helpful to say "users cannot reliably tell the difference between loading, empty, and error states."

## Define states first, then let components follow

Once the problem is clear, the implementation becomes easier to discuss. Before visual polish, write down the states the interface can enter and what each one must communicate.

- Loading should set expectations and preserve layout.
- Empty should explain why nothing is shown.
- Error should offer the next best recovery action.
- Success should get out of the way and feel effortless.

## A compact component API keeps these states readable

```jsx
function ResultsPanel({ status, data, onRetry }) {
  if (status === "loading") return <PanelSkeleton />;
  if (status === "error") return <ErrorState onRetry={onRetry} />;
  if (!data.length) return <EmptyState />;

  return <ResultsList items={data} />;
}
```

Code like this is short enough to scan and specific enough to support the surrounding explanation.

## Simple branching is often better than clever abstraction

One common temptation is to over-generalize UI state handling too early. A stronger technical article usually admits that some repetition is acceptable when it makes behavior easier to inspect.

## Takeaways

1. Describe the real user-facing problem, not the vague one.
2. Show one implementation slice that proves the idea.
3. Explain the tradeoff so the post feels honest.
