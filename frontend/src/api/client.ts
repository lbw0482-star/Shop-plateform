const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number
  detail?: string

  constructor(message: string, status: number, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
}

function buildUrl(path: string, query?: RequestOptions['query']) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value))
  })
  return url.toString()
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { query, headers, body, ...init } = options
  const response = await fetch(buildUrl(path, query), {
    ...init,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    credentials: 'include',
    headers: {
      ...(body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
  })

  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json') ? await response.json() : undefined
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : undefined
    throw new ApiError(detail ?? `请求失败（${response.status}）`, response.status, detail)
  }
  return (payload && typeof payload === 'object' && 'data' in payload ? payload.data : payload) as T
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query']) => request<T>(path, { method: 'GET', query }),
  post: <T>(path: string, body?: unknown, headers?: HeadersInit) => request<T>(path, { method: 'POST', body, headers }),
  patch: <T>(path: string, body?: unknown, headers?: HeadersInit) => request<T>(path, { method: 'PATCH', body, headers }),
  delete: <T>(path: string, body?: unknown) => request<T>(path, { method: 'DELETE', body }),
}

export async function getApiErrorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : '网络暂时不可用，请稍后再试'
}
