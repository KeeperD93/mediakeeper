import { PREVIEW_SAMPLES } from './preview-samples'
import { defaultTpl } from './defaults'

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function renderPreview(tpl, key, imageStyle, tplMeta, locale) {
  const sample = PREVIEW_SAMPLES[key] || PREVIEW_SAMPLES.added_movie
  imageStyle = imageStyle || 'image'
  const tmdbToken = '%%MK_SAFE_TMDB_LINK%%'
  const unknownToken = '%%MK_SAFE_UNKNOWN_PLACEHOLDER%%'
  let text = tpl || defaultTpl(tplMeta, locale, key)
  for (const [k, v] of Object.entries(sample)) {
    if (k === 'color' || k === 'poster' || k === 'tmdb_url') continue
    if (k === 'tmdb' && v && sample.tmdb_url) {
      text = text.replace(new RegExp('<tmdb>', 'g'), tmdbToken)
      continue
    }
    text = text.replace(new RegExp('<' + k + '>', 'g'), String(v || ''))
  }
  text = text.replace(/<imgur>/g, '')
  text = text.replace(/<fields>[^<]*<\/fields>/g, '')
  text = text.replace(/<[a-z_]+>/g, unknownToken)
  text = escapeHtml(text)
    .replaceAll(
      tmdbToken,
      `<a href="${sample.tmdb_url}" style="color:#00AFF4;text-decoration:none">${escapeHtml(sample.tmdb)}</a>`,
    )
    .replaceAll(unknownToken, '<em style="opacity:.35;font-style:normal">…</em>')

  const fmt = s =>
    s
      .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff">$1</strong>')
      .replace(
        /`([^`]+)`/g,
        '<code style="background:rgba(255,255,255,.1);padding:1px 4px;border-radius:3px;font-size:.7rem">$1</code>',
      )
      .replace(/\n/g, '<br/>')

  const parts = text.trim().split(/\n\n(.*)$/s)
  const contentAbove = parts.length > 1 ? fmt(parts[0]) : ''
  const embedText = parts.length > 1 ? fmt(parts[1]) : fmt(text.trim())

  const poster = sample.poster || ''
  const hasImgur = (tpl || defaultTpl(tplMeta, locale, key)).includes('<imgur>')
  let imgHtml = ''
  if (poster && hasImgur && imageStyle !== 'none') {
    if (imageStyle === 'thumbnail') {
      imgHtml = `<img src="${poster}" style="width:48px;height:68px;object-fit:cover;border-radius:3px;flex-shrink:0;float:right;margin-left:8px"/>`
    } else {
      imgHtml = `<img src="${poster}" style="max-width:140px;border-radius:3px;margin-top:8px;display:block"/>`
    }
  }

  let embed = '<div style="padding:4px 0;overflow:hidden">'
  if (imageStyle === 'thumbnail') embed += imgHtml
  embed += `<div style="font-size:.72rem;color:rgba(255,255,255,.55);line-height:1.5">${embedText}</div>`
  if (imageStyle === 'image') embed += imgHtml
  embed += '</div>'

  return { content: contentAbove || '', embed }
}
