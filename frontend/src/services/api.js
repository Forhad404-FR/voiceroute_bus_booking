// Thin fetch wrapper. Same-origin in production (FastAPI serves the SPA), proxied by Vite in development.
export class ApiError extends Error {
  constructor(message, status, data) { super(message); this.status = status; this.data = data }
}

function csrfToken() {
  const m = document.cookie.match(/(?:^|; )vr_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

async function request(method, path, { params, body } = {}) {
  let url = `/api${path}`
  if (params) {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') qs.append(k, v) })
    const s = qs.toString()
    if (s) url += `?${s}`
  }
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') headers['X-CSRF-Token'] = csrfToken()
  let res
  try {
    res = await fetch(url, { method, headers, credentials: 'same-origin', body: body !== undefined ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0)
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    const detail = data && data.detail
    const msg = typeof detail === 'string' ? detail : 'Request failed. Please try again.'
    throw new ApiError(msg, res.status, data)
  }
  return data
}

export const api = {
  get: (p, params) => request('GET', p, { params }),
  post: (p, body) => request('POST', p, { body: body ?? {} }),
  put: (p, body) => request('PUT', p, { body }),
  del: (p) => request('DELETE', p),
}
