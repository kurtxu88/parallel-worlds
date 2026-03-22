const rawPublicSiteUrl = import.meta.env.VITE_PUBLIC_SITE_URL?.trim()

export function getPublicSiteUrl() {
  if (!rawPublicSiteUrl) {
    return null
  }

  return rawPublicSiteUrl.replace(/\/+$/, '')
}

export function resolvePublicUrl(path = '/') {
  const siteUrl = getPublicSiteUrl()

  if (!siteUrl) {
    return path
  }

  return new URL(path, `${siteUrl}/`).toString()
}
