/**
 * commitlint config — MediaKeeper
 *
 * Standalone config (no ``extends``) so it resolves identically whether
 * commitlint is invoked from the repo root, from ``frontend/`` (CI), or
 * from a sibling tool that does not have ``@commitlint/config-conventional``
 * available on its ``node_modules`` path. The ruleset below is the
 * Conventional Commits subset MediaKeeper actually enforces.
 *
 * Allowed types:
 *   feat      new user-facing feature
 *   fix       bug fix
 *   refactor  code change that neither fixes a bug nor adds a feature
 *   perf      performance improvement
 *   docs      documentation only
 *   style     formatting / whitespace (no code change)
 *   test      adding / updating tests
 *   build     build system / dependencies
 *   ci        CI configuration
 *   chore     routine maintenance
 *   revert    revert a previous commit
 *
 * Message format:
 *   <type>(<scope>): <subject>
 *
 *   [optional body]
 *
 *   [optional footer(s)]
 */
export default {
  rules: {
    'type-empty': [2, 'never'],
    'subject-empty': [2, 'never'],
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'refactor', 'perf', 'docs', 'style', 'test', 'build', 'ci', 'chore', 'revert'],
    ],
    'subject-case': [0], // allow any case — French subjects too
    'body-max-line-length': [0], // long bodies OK
    'footer-max-line-length': [0],
    'header-max-length': [2, 'always', 120],
  },
}
