/**
 * Browser-side helper to push a JSON payload as a downloaded file.
 * Centralised so the admin Users page and the Security tab share the
 * exact same flow (revokeObjectURL included).
 */
export function downloadJsonFile(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
