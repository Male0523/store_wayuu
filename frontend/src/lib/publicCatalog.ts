import type { Page, Product } from '../types'

export interface PublicCatalogItem {
  id: number
  name: string
  categoryName: string
  price: string
  imageUrl: string
  description: string
  craftswomanName: string | null
  region: string
  color: string
  size: string
  productionTime: string
  stock: number
  madeToOrder: boolean
}

export function buildPublicCatalogParams(search: string, categoryId: number | null, page: number): URLSearchParams {
  const params = new URLSearchParams({ page: String(page), page_size: '100' })
  const normalizedSearch = search.trim()
  if (normalizedSearch) params.set('search', normalizedSearch)
  if (categoryId !== null) params.set('category', String(categoryId))
  return params
}

export function mapPublicCatalogProduct(product: Product): PublicCatalogItem {
  return {
    id: product.id,
    name: product.name,
    categoryName: product.category.name,
    price: product.price,
    imageUrl: product.image_url,
    description: product.description,
    craftswomanName: product.craftswoman?.name ?? null,
    region: product.region,
    color: product.color,
    size: product.size,
    productionTime: product.production_time,
    stock: product.stock,
    madeToOrder: product.made_to_order,
  }
}

export async function loadPublicCatalog(
  catalogApi: { products: (params: URLSearchParams) => Promise<Page<Product>> },
  search: string,
  categoryId: number | null,
): Promise<PublicCatalogItem[]> {
  const products: PublicCatalogItem[] = []
  let page = 1
  let pageCount = 1

  do {
    const result = await catalogApi.products(buildPublicCatalogParams(search, categoryId, page))
    products.push(...result.results.map(mapPublicCatalogProduct))
    pageCount = Math.max(1, Math.ceil(result.count / 100))
    page += 1
    if (!result.next || page > pageCount) break
  } while (true)

  return products
}
