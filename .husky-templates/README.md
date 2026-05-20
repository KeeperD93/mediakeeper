# Husky hooks — activation

These templates are ready to use as soon as the repository is a real Git
repository (`git init` then push to GitHub).

## Activation — 3 commands

```sh
cd <repo-root>
mkdir -p .husky
cp .husky-templates/pre-commit .husky/pre-commit
cp .husky-templates/commit-msg .husky/commit-msg
chmod +x .husky/pre-commit .husky/commit-msg
git config core.hooksPath .husky
```

That's it. From then on:

- **pre-commit** runs `lint-staged` on the staged files: ESLint + Prettier +
  stylelint auto-fix. A violation that cannot be auto-fixed blocks the commit.
- **commit-msg** validates the commit message against the Conventional Commits
  spec (`feat`, `fix`, `refactor`, etc.) — see `commitlint.config.js` at repo
  root.

## Bypass in an emergency

Never habitually. Use only if a hook itself is broken:

```sh
git commit --no-verify -m "…"
```

Investigate and fix the underlying issue immediately afterwards.
