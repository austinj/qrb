import rss from '@astrojs/rss';
import { pagesGlobToRssItems } from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const shows = await getCollection("shows");
  return rss({
    title: 'The Quadraphonic Rock Block',
    description: 'Music on KUCR',
    site: context.site,
    items: await pagesGlobToRssItems(import.meta.glob('./**/*.md')),
    items: shows.map((show) => ({
      title: show.data.title,
      pubDate: show.data.pubDate,
      description: show.data.description,
      link: `/shows/${show.id}/`,
    })),
    customData: `<language>en-us</language>`,
  })
}