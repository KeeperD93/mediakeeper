/**
 * Media Manager (file browser) enums.
 *
 * FILE_TYPE is the discriminator on `files[].type` returned by the
 * file-list API. RULE_TYPE drives the rename rule engine in
 * `composables/mediaManagerRules.js`. DIFF_TYPE tags chunks of the
 * rename preview diff.
 */
export const FILE_TYPE = Object.freeze({
  FILE: 'file',
  FOLDER: 'folder',
} as const)

export type FileType = (typeof FILE_TYPE)[keyof typeof FILE_TYPE]

export const RULE_TYPE = Object.freeze({
  REGEX: 'regex',
  REPLACE: 'replace',
} as const)

export type RuleType = (typeof RULE_TYPE)[keyof typeof RULE_TYPE]

export const DIFF_TYPE = Object.freeze({
  ADD: 'add',
  DEL: 'del',
} as const)

export type DiffType = (typeof DIFF_TYPE)[keyof typeof DIFF_TYPE]
