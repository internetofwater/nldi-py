# TDD Workflow

Follow this loop strictly. Do not skip steps or combine them.

## Cycle

1. **Red** — Write ONE failing test for the next behavior. Only one. Run `task tests`. Confirm
   it fails for the right reason. If it passes, the behavior already exists — pick a different one.
2. **Green** — Write the minimal code to make that test pass. Nothing more. Run `task tests`. Confirm
   all tests pass.
3. **Refactor** — Clean up the implementation if needed (remove duplication, improve naming, extract
   helpers). Do not change behavior. Run `task tests`. Confirm still green.
4. **Repeat** — Go back to step 1 for the next behavior.

## Rules

- Never write implementation code without a failing test driving it.
- Never write more than one test at a time before making it pass.
- "Minimal" means minimal. Do not anticipate future requirements.
- If a refactor breaks tests, undo it and try a smaller refactor.
- After each full cycle, briefly state what was added and what the next behavior to test is.

## Starting a new feature

Before the first cycle, list the behaviors to implement as a checklist. Work through them one at a
time. Update the checklist as you go.

## During a refactor

Same cycle applies. Write a characterization test for existing behavior first (confirm green), then
make the structural change, then confirm green again.

## Gall's Law Checkpoint

Before writing the first test, ask:

1. Does a simpler version of this feature already work that I can extend?
2. Am I building on a working system, or designing something new from scratch?
3. If from scratch, what is the smallest working subset I can deliver first?

Order the behavior checklist so that the earliest items produce a working (if minimal) feature. Later
items extend it. Every checklist item should leave the system working.
