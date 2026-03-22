import { getCurrentInstance } from 'vue'
import { useHead } from '@unhead/vue'
import { getPublicSiteUrl, resolvePublicUrl } from './site'

interface PageSeoOptions {
  title: string
  description: string
  path?: string
  imagePath?: string
  noindex?: boolean
}

const SITE_NAME = 'Parallel Worlds'

export function usePageSeo({
  title,
  description,
  path = '/',
  imagePath = '/social-card.svg',
  noindex = false
}: PageSeoOptions) {
  const siteUrl = getPublicSiteUrl()
  const canonicalUrl = siteUrl ? resolvePublicUrl(path) : null
  const imageUrl = resolvePublicUrl(imagePath)
  const head = getCurrentInstance()?.appContext.config.globalProperties.$head

  if (!head) {
    // Some unit tests mount components without installing the head plugin.
    return
  }

  useHead(
    {
      title,
      meta: [
        { name: 'description', content: description },
        { property: 'og:site_name', content: SITE_NAME },
        { property: 'og:type', content: 'website' },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:image', content: imageUrl },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: title },
        { name: 'twitter:description', content: description },
        { name: 'twitter:image', content: imageUrl },
        { name: 'robots', content: noindex ? 'noindex,nofollow' : 'index,follow' }
      ],
      link: canonicalUrl
        ? [
            { rel: 'canonical', href: canonicalUrl }
          ]
        : []
    },
    { head }
  )
}
