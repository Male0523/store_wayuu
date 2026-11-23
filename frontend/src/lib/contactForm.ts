export interface ContactSubmission {
  name: string
  email: string
  subject: string
  message: string
  website: string
}

export type ContactSubmissionState = 'idle' | 'sending' | 'success' | 'error'

export function contactPayloadFromForm(formData: FormData): ContactSubmission {
  return {
    name: String(formData.get('name') ?? ''),
    email: String(formData.get('email') ?? ''),
    subject: String(formData.get('subject') ?? ''),
    message: String(formData.get('message') ?? ''),
    website: String(formData.get('website') ?? ''),
  }
}

export function createContactSubmitter(
  send: (payload: ContactSubmission) => Promise<unknown>,
) {
  let pending = false

  return async (
    payload: ContactSubmission,
    onState: (state: ContactSubmissionState, error?: unknown) => void,
  ): Promise<boolean> => {
    if (pending) return false
    pending = true
    onState('sending')

    try {
      await send(payload)
      onState('success')
      return true
    } catch (error) {
      onState('error', error)
      return false
    } finally {
      pending = false
    }
  }
}
