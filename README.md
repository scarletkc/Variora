# Variora

Different models, the same brief. A collection of demos built from shared prompts, with source code, screenshots, and notes for comparing the results.

## Projects

- [Rainy Ramen](projects/rainy-ramen/): a cat-run ramen shop illustrated in SVG and presented in HTML.
- [Neon Serpent](projects/neon-serpent/): a first-person snake game in a futuristic Japanese city.

## Layout

```text
projects/
  <project>/
    PROMPT.md                 # Shared prompt
    README.md                 # Results and links
    models/
      <model>/
        README.md             # Model, harness, assistance, and run instructions
        app/                  # Implementation
        screenshots/          # Optional captures
templates/
  project/
  model/
```

## Add a comparison

Copy the [project template](templates/project/) into `projects/<project>/` and write a concise shared prompt. Each model follows the [repository rules](AGENTS.md), keeps its implementation in `models/<model>/app/`, and uses the [model record template](templates/model/README.md) for its README. Link the results from the project README.
