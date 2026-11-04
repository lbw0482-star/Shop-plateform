export const queryKeys = {
  me: ['auth', 'me'] as const,
  products: (params: Record<string, unknown>) => ['products', params] as const,
  product: (id: number | string) => ['product', id] as const,
  cart: ['cart'] as const,
  orders: (params: Record<string, unknown>) => ['orders', params] as const,
  order: (id: number | string) => ['order', id] as const,
  messages: (scope: string) => ['messages', scope] as const,
}
