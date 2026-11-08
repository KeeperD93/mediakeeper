/** Steps of the setup wizard, in the order they are shown. */
export const ONBOARDING_STEP = Object.freeze({
  WELCOME: 'welcome',
  LOCALE: 'locale',
  EMBY: 'emby',
  TMDB: 'tmdb',
  OPENSUBTITLES: 'opensubtitles',
  FOLDERS: 'folders',
  TOUR: 'tour',
  DONE: 'done',
} as const)

export type OnboardingStep = (typeof ONBOARDING_STEP)[keyof typeof ONBOARDING_STEP]
