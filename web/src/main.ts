import '@fontsource/im-fell-english/400.css'
import '@fontsource/im-fell-english/400-italic.css'
import '@fontsource/im-fell-english-sc/400.css'
import '@fontsource/jacquard-24/400.css'
import 'leaflet/dist/leaflet.css'
import './style.css'
import { Atlas } from './atlas'
import type { Index } from './types'
import { ui } from './ui'
import { $, getJSON } from './util'

try {
  const index = await getJSON<Index>('maps/index.json')
  if (!index.worlds.length) throw new Error('404')
  document.title = $('title').textContent = index.title
  $('realm').textContent = index.subtitle
  const atlas = new Atlas($('map'), index, $('readout'))
  ui(atlas)
  const view = atlas.parse(location.hash)
  await (view ? atlas.show(view) : atlas.open(index.worlds[0].id))
} catch (e) {
  console.error(e)
  const unpublished = e instanceof Error && e.message.includes('404')
  document.body.classList.add('blank')
  $('realm').textContent = unpublished
    ? 'No world has been charted yet. Run python tools/atlas.py publish on the server computer.'
    : 'The chart could not be fetched. Check your connection and reload the page.'
}
