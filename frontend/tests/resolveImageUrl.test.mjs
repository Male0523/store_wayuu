import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveImageUrl } from '../src/lib/imageUrl.ts'

test('rewrites loopback media URLs to same-origin paths', () => {
  assert.equal(
    resolveImageUrl('http://127.0.0.1:8000/media/products/imagen.jpg'),
    '/media/products/imagen.jpg',
  )
  assert.equal(
    resolveImageUrl('http://localhost:8000/media/products/imagen.jpg'),
    '/media/products/imagen.jpg',
  )
})

test('preserves external HTTP and HTTPS image URLs', () => {
  assert.equal(resolveImageUrl('https://images.example.com/manta.jpg'), 'https://images.example.com/manta.jpg')
  assert.equal(resolveImageUrl('http://images.example.com/manta.jpg'), 'http://images.example.com/manta.jpg')
})

test('preserves relative paths and data images', () => {
  const relativePath = '/media/products/imagen.jpg'
  const dataUrl = 'data:image/jpeg;base64,/9j/4AAQSkZJRg=='
  assert.equal(resolveImageUrl(relativePath), relativePath)
  assert.equal(resolveImageUrl(dataUrl), dataUrl)
})

test('handles missing and malformed values safely', () => {
  assert.equal(resolveImageUrl(''), '')
  assert.equal(resolveImageUrl('   '), '')
  assert.equal(resolveImageUrl(null), '')
  assert.equal(resolveImageUrl(undefined), '')
  assert.equal(resolveImageUrl('http://['), '')
})
