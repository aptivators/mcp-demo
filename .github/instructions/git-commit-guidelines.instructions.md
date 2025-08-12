---
applyTo: "**"
---
# Git Commit Guidelines

## Description
Standards and best practices for writing Git commit messages in our project. Following these guidelines helps maintain a clean, readable, and maintainable Git history.

## Rules

### Commit Message Structure
```regex
^(feat|fix|docs|style|refactor|perf|test|chore|ci)(\([a-z-]+\))?: .{1,50}$
```
Commit message must follow the format: type(scope): subject (max 50 chars)

### Commit Message Body
```regex
^.{1,72}$
```
Commit message body lines should not exceed 72 characters

### Commit Message Type
```regex
^(feat|fix|docs|style|refactor|perf|test|chore|ci):
```
Commit type must be one of: feat, fix, docs, style, refactor, perf, test, chore, ci

### Commit Message Subject
```regex
^[a-z]
```
Commit subject should start with lowercase letter

### Commit Message Period
```regex
^[^.]*[^.]$
```
Commit subject should not end with a period

## Examples

### Valid Commit Messages
```text
feat(auth): implement OAuth2 authentication
fix(api): resolve rate limiting issue
docs: update API documentation
```

### Invalid Commit Messages
```text
Fixed stuff
Updated code
More changes
WIP
Fixed bug
```

## References
- [Conventional Commits](mdc:https:/www.conventionalcommits.org)
- [Angular Commit Guidelines](mdc:https:/github.com/angular/angular/blob/master/CONTRIBUTING.md#commit)
- [Git Commit Message Best Practices](mdc:https:/chris.beams.io/posts/git-commit)

