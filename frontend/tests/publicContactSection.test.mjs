import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = await readFile(new URL('../../sitio_p_blico_tienda_artesanal_way_u.tsx', import.meta.url), 'utf8')
const start = source.indexOf('<section id="contacto"')
const end = source.indexOf('</section>', start)
assert.notEqual(start, -1, 'the public contact section remains registered for existing navigation')
assert.notEqual(end, -1, 'the public contact section has a closing tag')
const section = source.slice(start, end)

test('shows the authorized phone and opens the device dialer', () => {
  assert.match(section, /href="tel:3127768141"/)
  assert.match(section, /312 776 8141/)
})

test('shows the authorized email and opens a mail client', () => {
  assert.match(section, /href="mailto:maleja23sm@gmail\.com"/)
  assert.match(section, /maleja23sm@gmail\.com/)
})

test('shows only the authorized general location and no old demonstration contacts or form', () => {
  assert.match(section, /Riohacha, La Guajira, Colombia/)
  assert.doesNotMatch(section, /Calle 15 # 8-42|300 000 0000|605 000 0000|contacto\.demo@tiendawayuu\.co/)
  assert.match(source, /href="tel:3127768141"/)
  assert.match(source, /href="mailto:maleja23sm@gmail\.com"/)
  assert.doesNotMatch(source, /Calle 15 # 8-42|\+57 300 000 0000 \(Demostración\)|\+57 605 000 0000|contacto\.demo@tiendawayuu\.co/)
  assert.doesNotMatch(section, /<form|type="submit"|mensaje enviado|consulta fue procesada/i)
})

test('uses responsive layout and preserves the existing institutional copy', () => {
  assert.match(section, /grid-cols-1 lg:grid-cols-12/)
  assert.match(section, /Nuestro Propósito/)
  assert.match(section, /salvaguardar el legado textil de la etnia Wayúu/)
  assert.match(source, /Nuestra Historia: El Mito de Wale’kerü/)
  assert.match(source, /¿Qué Hacemos en Nuestra Tienda\?/)
})
