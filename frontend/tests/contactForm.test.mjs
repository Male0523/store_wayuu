import assert from 'node:assert/strict'
import test from 'node:test'
import { contactPayloadFromForm, createContactSubmitter } from '../src/lib/contactForm.ts'

test('builds the contact request from the existing form fields, including the honeypot', () => {
  const formData = new FormData()
  formData.set('name', ' Ana Wayúu ')
  formData.set('email', 'ana@example.test')
  formData.set('subject', 'Consulta')
  formData.set('message', '¿Tienen mantas?')
  formData.set('website', '')

  assert.deepEqual(contactPayloadFromForm(formData), {
    name: ' Ana Wayúu ',
    email: 'ana@example.test',
    subject: 'Consulta',
    message: '¿Tienen mantas?',
    website: '',
  })
})

test('reports sending and success only after the API request resolves', async () => {
  const states = []
  let resolveSend
  const submit = createContactSubmitter(() => new Promise((resolve) => { resolveSend = resolve }))
  const pending = submit({ name: 'Ana', email: 'ana@example.test', subject: 'Hola', message: 'Consulta', website: '' }, (state) => states.push(state))

  assert.deepEqual(states, ['sending'])
  resolveSend({ detail: 'ok' })
  assert.equal(await pending, true)
  assert.deepEqual(states, ['sending', 'success'])
})

test('prevents a duplicate while a contact request is pending', async () => {
  let resolveSend
  let sendCount = 0
  const submit = createContactSubmitter(() => {
    sendCount += 1
    return new Promise((resolve) => { resolveSend = resolve })
  })
  const payload = { name: 'Ana', email: 'ana@example.test', subject: 'Hola', message: 'Consulta', website: '' }
  const states = []
  const first = submit(payload, (state) => states.push(state))

  assert.equal(await submit(payload, (state) => states.push(state)), false)
  assert.equal(sendCount, 1)
  resolveSend()
  assert.equal(await first, true)
  assert.deepEqual(states, ['sending', 'success'])
})

test('reports a failed request without changing the submitted data', async () => {
  const payload = { name: 'Ana', email: 'ana@example.test', subject: 'Hola', message: 'Consulta', website: '' }
  const original = { ...payload }
  const states = []
  const submit = createContactSubmitter(async () => { throw new Error('private SMTP detail') })

  assert.equal(await submit(payload, (state, error) => states.push([state, error?.message])), false)
  assert.deepEqual(states, [['sending', undefined], ['error', 'private SMTP detail']])
  assert.deepEqual(payload, original)
})
