# AGENTS.md

## Purpose

This file provides general instructions for AI coding agents working in this repository.

Read `README.md` first to understand the project.

Follow the rules defined in:

* `docs/project_rules.md`
* `docs/user_rules.md`

## Before Making Changes

Before modifying code:

1. Understand the relevant part of the project.
2. Read the existing implementation.
3. Search for existing functionality before creating new functionality.
4. Follow the existing architecture and coding patterns.
5. Identify the smallest safe change that solves the problem.

Do not modify unrelated code.

## Implementation

When implementing changes:

1. Keep the change focused.
2. Reuse existing code where appropriate.
3. Follow existing naming and structure conventions.
4. Avoid unnecessary dependencies.
5. Avoid unnecessary refactoring.
6. Preserve existing behavior unless the task requires changing it.

## Architecture

Respect the existing project architecture.

Do not introduce a new architectural pattern, framework, service, or dependency without a clear reason.

If a proposed change significantly affects the architecture, explain the impact before implementation.

## Files and Configuration

* Do not overwrite unrelated files.
* Do not delete files unless they are no longer required.
* Do not modify generated files unless necessary.
* Do not commit secrets or credentials.
* Do not expose API keys, passwords, tokens, or private configuration.

## Database and Data

Before modifying database schemas or data:

1. Inspect the existing schema.
2. Understand the impact.
3. Prefer non-destructive operations.
4. Never perform destructive operations without appropriate confirmation.

For `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, migrations, or other potentially destructive operations, verify the affected scope before execution.

## Testing

After making changes:

1. Run relevant tests.
2. Run relevant build or validation commands.
3. Check for errors.
4. Verify that existing functionality has not been unnecessarily affected.

If tests cannot be run, explain why.

## Error Handling

When fixing an error:

1. Identify the root cause.
2. Explain the cause briefly.
3. Implement the smallest appropriate fix.
4. Test the fix.
5. Report the result.

Do not hide or ignore errors simply to make a command succeed.

## Git

* Do not force push.
* Do not reset or discard user changes without explicit approval.
* Do not delete branches without approval.
* Do not overwrite unrelated uncommitted changes.
* Keep commits focused when creating commits.

## Communication

When reporting completed work, summarize:

* What changed
* Why it changed
* Files affected
* Tests or validation performed
* Any remaining issues

## Important

When project-specific rules conflict with these general instructions, follow the more specific project instructions.
