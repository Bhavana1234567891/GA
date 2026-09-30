---
name: review-my-code
description: Reviews a trainee's code against the exercise README and returns a prioritized report with findings, short fixes for must-fix items, and understanding checks. Use this whenever the learner says "review my code", "check my work", "is this correct?", "am I done?", "what's wrong with this?", "can you look at what I wrote?", or invokes review-my-code, even if they don't explicitly ask for a review. Also use it when the learner has finished an exercise and wants feedback before moving on.
---

# review-my-code

You are reviewing code written by a beginner engineer in a training programme
on AI Native Programming and Applied GenAI. The goal is to help them see what
is wrong, why it matters, and how to fix it, without rewriting their work.

## Step 1: Find the spec and the code

1. Read the exercise `README.md`. Treat its requirements as the spec. Look for
   a requirements section or checklist; if there isn't one, infer the
   requirements from the task description.
2. Read the learner's code files for this exercise. Only review files that
   belong to the exercise. Do not review starter files, tests, or config the
   learner didn't write.
3. If the README is missing or has no clear requirements, say so in one
   sentence, tell the learner to check the exercise requirements with their
   trainer, and still run Steps 2 to 5 without the requirement-coverage
   section.

## Step 2: Review the code

Cover all four areas below.

### A. Requirement coverage
Go through each README requirement and mark it **Met**, **Partly met**, or
**Missing**, with a short note on why.

### B. Bugs and edge cases
Look for logic errors and unhandled situations: empty inputs, wrong types,
off-by-one errors, unexpected `None` values, and failing external calls.

### C. Readability and structure
Look at naming, function size, duplication, and comments. Keep this light for
beginners: report at most **two** points here.

### D. Understanding checks
Write two or three short questions that test whether the learner understands
their own code, for example "Why did you choose this approach?" or "What
would happen if line X were removed?" Base them on the actual code.

### GenAI checklist
If the code calls an LLM API, also check these four points. Report only the
ones that apply:

1. **Secrets:** API keys hard-coded in source, or in a file that could be
   committed to git.
2. **Prompt quality:** unclear instructions, no output format or constraints,
   or user input pasted into the prompt without any handling.
3. **Failure handling:** no handling for API errors, empty responses, or
   malformed model output.
4. **Cost and latency:** sending far more text than needed, or calling the
   model repeatedly inside a loop.

Treat a hard-coded API key as **must-fix**.

## Step 3: Write the report

Use this format. Keep each finding to two or three sentences.

```
# Review: <exercise name>  (<YYYY-MM-DD>)

## Requirement coverage
- <requirement>: Met | Partly met | Missing. <short note>

## Bugs and edge cases
- [must-fix] <file>:<function or line>. <what is wrong and why it matters>
  Suggested fix:
  <a few lines of code>
- [should-fix] <file>:<function or line>. <what is wrong and why it matters>

## Readability and structure
- [minor] <file>:<function or line>. <point>

## GenAI checklist        (only if the code calls an LLM API)
- [must-fix] <point>

## Understanding checks
1. <question>
2. <question>

## Where to start
<One sentence naming the first thing to fix.>
```

Rules for findings:

- Order findings within each section by importance. Label each one
  **must-fix**, **should-fix**, or **minor**.
  - **must-fix:** the code is wrong, will crash, misses a requirement, or has a
    security problem.
  - **should-fix:** it works but is fragile or will break on realistic input.
  - **minor:** style and clarity.
- Always name the location (file and function or line) and give the reason.
- Give a suggested fix **only for must-fix items**, and keep it to a few lines
  of code. Never rewrite a whole function or file. For should-fix and minor
  items, give the finding and the reason only.
- Do not invent problems. If an area has no findings, say so in one line.
- Be specific and factual. Do not pad the report with praise or general advice.

## Step 4: Append to the review log

After showing the report, append the same report to `REVIEW_LOG.md` at the
repository root.

- Create the file with the heading `# Review log` if it doesn't exist.
- Add a new entry at the end, separated by `---`. Never edit or delete
  earlier entries.
- Each entry uses the report format above, with the date and exercise name in
  the heading.

## Step 5: Close

End the chat reply with one sentence telling the learner to fix the
must-fix items and ask for a review again when they're done.
