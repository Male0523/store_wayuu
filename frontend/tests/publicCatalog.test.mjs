import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPublicCatalogParams, loadPublicCatalog, mapPublicCatalogProduct } from '../src/lib/publicCatalog.ts'

test('builds server-side search and category filters without demo values', () => {
  const params = buildPublicCatalogParams('  manta  ', 7, 2)
  assert.equal(params.get('search'), 'manta')
  assert.equal(params.get('category'), '7')
  assert.equal(params.get('page'), '2')
  assert.equal(params.get('page_size'), '100')
})

test('omits empty search and category filters', () => {
  const params = buildPublicCatalogParams('  ', null, 1)
  assert.equal(params.has('search'), false)
  assert.equal(params.has('category'), false)
  assert.equal(params.get('page'), '1')
})

test('maps only verified product fields and preserves missing artisan/image values', () => {
  const item = mapPublicCatalogProduct({
    id: 4,
    sku: 'MNT-004',
    name: 'Manta real',
    category: { id: 2, name: 'Mantas', description: '' },
    craftswoman: null,
    description: 'Descripción registrada',
    region: 'Uribia',
    color: 'Azul',
    size: 'M',
    production_time: '10 días',
    price: '125000.00',
    stock: 3,
    image_url: '',
    made_to_order: false,
    created_at: '',
    updated_at: '',
  })

  assert.deepEqual(item, {
    id: 4,
    name: 'Manta real',
    categoryName: 'Mantas',
    price: '125000.00',
    imageUrl: '',
    description: 'Descripción registrada',
    craftswomanName: null,
    region: 'Uribia',
    color: 'Azul',
    size: 'M',
    productionTime: '10 días',
    stock: 3,
    madeToOrder: false,
  })
})

test('loads filtered product pages from the API client until the result set is complete', async () => {
  const requests = []
  const product = (id) => ({
    id,
    sku: `SKU-${id}`,
    name: `Manta ${id}`,
    category: { id: 7, name: 'Mantas', description: '' },
    craftswoman: null,
    description: '',
    region: '',
    color: '',
    size: '',
    production_time: '',
    price: '100000.00',
    stock: 1,
    image_url: '',
    made_to_order: false,
    created_at: '',
    updated_at: '',
  })
  const catalogApi = {
    async products(params) {
      requests.push(params)
      const page = Number(params.get('page'))
      return {
        count: 101,
        next: page === 1 ? 'http://api.test/products/?page=2' : null,
        previous: null,
        results: page === 1 ? Array.from({ length: 100 }, (_, index) => product(index + 1)) : [product(101)],
      }
    },
  }

  const products = await loadPublicCatalog(catalogApi, ' manta ', 7)

  assert.equal(products.length, 101)
  assert.equal(products[0].id, 1)
  assert.equal(products[100].id, 101)
  assert.equal(requests.length, 2)
  for (const params of requests) {
    assert.equal(params.get('search'), 'manta')
    assert.equal(params.get('category'), '7')
    assert.equal(params.get('page_size'), '100')
  }
  assert.deepEqual(requests.map((params) => params.get('page')), ['1', '2'])
})
