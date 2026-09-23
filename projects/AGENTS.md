# Model implementation work

## Isolation

When generating or revising a demo, do not read, search, copy, or reference another model's implementation code or generated output, such as MIDI files or audio, in this repository, including through Git history, tools, skills, or subagents.

Do not use persistent memory, prior-session history, or notes from previous runs. Do not read from or write to memory files, services, or plugins, including through tools or subagents. Use only the current run's instructions and allowed inputs.

## Contribution guidelines

Read the entire [contribution guide](../CONTRIBUTING.md) before starting an implementation or making review follow-up changes, and follow its applicable requirements.

## Implementation workflow

1. Before creating any implementation files or writing code, create and switch to a new branch for one model implementation in one project. Do not begin implementation on `main` or another implementation's branch.
2. Implement the project prompt and fill in the [model record](../templates/model/README.md).
3. Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages and PR titles.
4. Commit and push the model's branch, then create a pull request targeting `main`. Leave the PR open for review.
5. Present the created PR URL with a short summary of the result and checks performed.
