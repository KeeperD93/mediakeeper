/**
 * Shared pagination constants for the portal list pagers (requests, tickets, …).
 * Page-size options stay within the 1–100 `per_page` bound enforced by the
 * paginated portal endpoints.
 */
export const PAGE_SIZES = Object.freeze([10, 25, 50, 100] as const)

export const DEFAULT_PAGE_SIZE = 25
