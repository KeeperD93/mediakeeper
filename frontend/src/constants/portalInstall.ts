/** How the portal installs as an app on this browser. */
export const INSTALL_WAY = Object.freeze({
  /** The browser's own install window: Chrome, Edge, Android. */
  PROMPT: 'prompt',
  /** Steps to follow, Share then « Add to Home Screen »: iPhone and iPad. */
  IOS: 'ios',
  /** Steps to follow, File then « Add to Dock »: Safari on a Mac. */
  MAC: 'mac',
  /** Steps to follow, its menu then « Add app to Home screen »: Firefox on Android. */
  FIREFOX_ANDROID: 'firefox-android',
  /** No install here: another browser to open the portal in. Firefox on a computer. */
  OTHER_BROWSER: 'other-browser',
} as const)

export type InstallWay = (typeof INSTALL_WAY)[keyof typeof INSTALL_WAY]
