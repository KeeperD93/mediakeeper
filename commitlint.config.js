/**
 * commitlint config — MediaKeeper
 *
 * Enforces the Conventional Commits spec (https://www.conventionalcommits.org).
 * Enables clean auto-generated changelogs later.
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
 *
 * Examples:
 *   feat(portal): add trophy unlock toast
 *   fix(media-manager): handle empty filename in rename batch
 *   refactor(stats): split StatsUsersTab into composable
 *   chore(deps): bump vite to 6.2.4
 */
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
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
