# A debugging journal format that stays useful later

## Why a journal helps

Small production bugs often take longer than expected because the reasoning disappears after the fix. A lightweight debugging journal helps preserve what was tried, what failed, and why the final change worked.

## A simple structure

Use the same five sections each time:

1. Symptom
2. Hypothesis
3. Evidence
4. Fix
5. Lesson

## Example

### Symptom

The article list sometimes rendered empty after a fast page refresh.

### Hypothesis

Client state was being read before the async content finished loading.

### Evidence

- Reproduced only on hard refresh.
- Disappeared after a second render.
- Network response arrived after the initial UI branch decision.

### Fix

Move the empty state behind a resolved loading flag instead of checking array length too early.

### Lesson

A good bug write-up is not just a diary. It becomes reusable team knowledge.
