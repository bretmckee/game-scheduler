---
description: 'Project-specific enhancements for task-researcher chatmode behavior'
applyTo: '.github/chatmodes/task-researcher.chatmode.md'
---

# Task Researcher Enhancements

## Software Version Recommendation Policy

When researching and recommending software, libraries, frameworks, or tools, you MUST follow these version selection guidelines:

### Version Selection Rules

You MUST recommend ONE of the following:
- **Latest Released Version**: The most recent stable release
- **Latest Long-Term Support (LTS) Version**: The most recent version with extended support

### Selection Criteria

You MUST choose the version with the **longer support lifecycle**:

1. **Compare Support End Dates**:
   - Identify the support end date for the latest released version
   - Identify the support end date for the latest LTS version
   - Recommend the version that will be supported longer

2. **Document Your Decision**:
   - State which version you are recommending
   - Provide the support end date or support duration
   - Explain why this version was selected over the alternative
   - Include links to official support lifecycle documentation

### Required Documentation

For each software recommendation, you MUST include:

```markdown
### Recommended Version

**Software**: {{software_name}}
**Recommended Version**: {{version_number}}
**Type**: {{Latest Release | LTS}}
**Support Until**: {{end_date or duration}}
**Reasoning**: {{why this version was selected}}
**Source**: {{official_documentation_url}}

**Alternative Considered**:
- {{alternative_version_type}}: {{version_number}} (Support until: {{date}})
```

### Examples

#### Example 1: LTS Has Longer Support

```markdown
### Recommended Version

**Software**: Node.js
**Recommended Version**: 20.x
**Type**: LTS (Iron)
**Support Until**: April 2026 (Active) / April 2027 (Maintenance)
**Reasoning**: LTS version provides 3+ years of support, while latest (22.x) has standard release cycle
**Source**: https://github.com/nodejs/release#release-schedule

**Alternative Considered**:
- Latest Release: 22.x (Support until: April 2025)
```

#### Example 2: Latest Release Has Longer Support

```markdown
### Recommended Version

**Software**: Python
**Recommended Version**: 3.13
**Type**: Latest Release
**Support Until**: October 2029 (5 years from release)
**Reasoning**: Latest release provides full 5-year support lifecycle
**Source**: https://devguide.python.org/versions/

**Alternative Considered**:
- Previous LTS: 3.11 (Support until: October 2027)
```

### Edge Cases

**When Support Durations Are Equal or Unknown**:
- Prefer Latest Release for access to newest features and improvements
- Document that support lifecycles are comparable
- Note any other factors influencing the decision

**When No Official LTS Exists**:
- Recommend Latest Stable Release
- Document the project's versioning and support policy
- Note absence of formal LTS program

**When Multiple LTS Versions Are Available**:
- Choose the Latest LTS version
- Compare only against the latest non-LTS release
- Document all active LTS versions for reference

## Research Quality Standards

These version guidelines supplement the core research principles:
- You WILL verify version information from official sources
- You WILL check release dates and support schedules
- You WILL update recommendations when newer versions are discovered
- You WILL remove outdated version recommendations immediately
