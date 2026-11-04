import type { CartItem, CurrentUser, Message, Order, PageResult, Product } from '../types'

export function normalizeUser(raw: any): CurrentUser {
  return {
    id: raw?.id ?? raw?.user_id ?? raw?.admin_id,
    username: raw?.username ?? raw?.admin_name ?? '',
    display_name: raw?.display_name ?? raw?.real_name ?? null,
    role: raw?.role ?? (raw?.roles?.includes?.('SUPER_ADMIN') ? 'SUPER_ADMIN' : raw?.roles ? 'OPER_ADMIN' : 'MEMBER'),
    total_points: raw?.total_points ?? 0,
    level_name: raw?.level_name ?? null,
    must_change_password: raw?.must_change_password ?? false,
  }
}

export function normalizeProduct(raw: any): Product {
  return {
    ...raw,
    id: raw?.id ?? raw?.product_id,
    product_id: raw?.product_id ?? raw?.id,
  }
}

export function normalizeProductPage(raw: any): PageResult<Product> {
  return { ...raw, items: (raw?.items ?? []).map(normalizeProduct) }
}

export function normalizeCart(raw: any): { items: CartItem[]; total_amount: number | string } {
  const items = (raw?.items ?? []).map((item: any) => {
    const product = normalizeProduct(item.product ?? item)
    return {
      id: item.id ?? item.cart_item_id,
      cart_item_id: item.cart_item_id ?? item.id,
      product_id: product.id,
      product_name: product.product_name,
      unit_price: product.unit_price,
      quantity: item.quantity,
      stock_qty: product.stock_qty,
      subtotal: item.subtotal ?? Number(product.unit_price) * item.quantity,
    }
  })
  return { ...raw, items }
}

export function normalizeOrder(raw: any): Order {
  return { ...raw, id: raw?.id ?? raw?.order_id, order_id: raw?.order_id ?? raw?.id }
}

export function normalizeOrderPage(raw: any): PageResult<Order> {
  return { ...raw, items: (raw?.items ?? []).map(normalizeOrder) }
}

export function normalizeMessage(raw: any): Message {
  const replies = raw?.replies ?? []
  const lastReply = replies.length ? replies[replies.length - 1] : undefined
  return { ...raw, id: raw?.id ?? raw?.message_id, message_id: raw?.message_id ?? raw?.id, reply_content: raw?.reply_content ?? lastReply?.content ?? null }
}

export function normalizeMessages(raw: any): Message[] {
  return (raw ?? []).map(normalizeMessage)
}
