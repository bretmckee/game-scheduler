---
description: 'Interactive brainstorming session using task-researcher capabilities'
---

<!-- markdownlint-disable-file -->

# Brainstorming Session

You WILL follow the same research principles as the task-researcher subagent (`.claude/agents/task-researcher.md`) with the following critical modifications for brainstorming mode.

## Primary Directive

Conduct an interactive brainstorming session that leverages task-researcher-style contextual discovery WITHOUT creating formal research documentation until explicitly requested.

## Scope & Preconditions

- **Mode**: Exploratory and conversational rather than formal documentation
- **Behavior Base**: Same research principles and tools as the task-researcher subagent, with modified output behavior
- **Output**: Conversational exploration and discovery; formal research report only when explicitly requested
- **Key Modification**: Suspend the default behavior of creating files in `.copilot-tracking/research/` until signaled by the user

## Inputs

- **Topic** (required): The subject, problem, or question to explore (`$ARGUMENTS` or the user's initial message)
- **Context** (gathered): Relevant existing code, patterns, and implementations discovered through research tools
- **Preferences** (clarified): User priorities, constraints, and trade-offs identified through interactive questioning

## Workflow

### 1. Understand the Topic

- Ask clarifying questions to understand the problem space, opportunity, or question
- Identify constraints, requirements, and relevant context
- Determine the scope and boundaries of exploration

### 2. Conduct Interactive Research

- Use Grep/Glob to analyze project structure and existing implementations
- Use Grep to find relevant code patterns and configurations
- Use Grep to understand how patterns are applied across the codebase
- Use WebFetch to gather official documentation and specifications from a known URL
- Use WebSearch to research implementation patterns and best practices, including from other projects
- Read relevant files to examine existing conventions and standards

### 3. Share Discoveries Conversationally

- Present findings in conversational format rather than formal documentation
- Ask follow-up questions about preferences, priorities, and trade-offs
- Dig deeper based on user responses and interests
- Reference external examples and best practices during exploration

### 4. Explore Alternatives

- Research multiple approaches without prematurely recommending one
- Discuss pros, cons, and implications of different options
- Consider edge cases, integration points, and potential challenges
- Keep exploration flexible and avoid early convergence

### 5. Wait for Formalization Signal

- Continue interactive exploration until user indicates readiness
- Recognize signals such as "create the research report", "formalize this", or "document our findings"
- ONLY THEN create formal documentation in `.copilot-tracking/research/`, following the task-researcher subagent's template and guidelines (invoke it directly for this step)

## Output Expectations

### During Brainstorming

- Present findings conversationally with clear explanations
- Share code examples, patterns, and references inline
- Highlight trade-offs and alternatives without forcing decisions
- Ask clarifying questions to guide exploration depth

### Upon Formalization Request

- Create formal research document in `.copilot-tracking/research/` using date-prefixed naming: `YYYYMMDD-NN-topic-description-research.md`
- Follow the task-researcher subagent's template structure
- Include verified findings from research tools
- Document selected approach with implementation guidance
- Remove non-selected alternatives from final documentation

## Quality Assurance

Brainstorming session is successful when:

- [ ] Topic and exploration scope are clearly understood
- [ ] Relevant context gathered from multiple authoritative sources
- [ ] Multiple approaches explored and discussed with evidence
- [ ] User questions answered and uncertainties addressed
- [ ] Findings presented conversationally without premature documentation
- [ ] Formal research report created only when explicitly requested
- [ ] Final documentation follows task-researcher template and standards

## Guard Rails

- Do NOT create files in `.copilot-tracking/research/` until user explicitly requests formalization
- Do NOT converge on a single solution prematurely
- Do use research tools throughout the conversation to provide evidence-based exploration
- Do maintain conversational tone rather than formal documentation style during exploration

## Related Resources

- [task-researcher subagent](../agents/task-researcher.md) - Base behavior with standard research principles
