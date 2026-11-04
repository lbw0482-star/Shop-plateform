export type Role = 'MEMBER' | 'OPER_ADMIN' | 'SUPER_ADMIN'

export interface CurrentUser {
  id: number
  username: string
  display_name?: string | null
  role: Role
  total_points?: number
  level_name?: string | null
  must_change_password?: boolean
}

export interface Product {
  id: number
  product_id?: number
  product_code: string
  product_name: string
  category_id: number
  category_name?: string | null
  stock_qty: number
  unit_price: number | string
  product_intro?: string | null
  product_points: number
  recommend_flag: boolean
  product_status: 'D' | 'O' | 'X'
  main_image_url?: string | null
}

export interface CartItem {
  id: number
  cart_item_id?: number
  product_id: number
  product_name: string
  unit_price: number | string
  quantity: number
  stock_qty: number
  subtotal: number | string
}

export interface Order {
  id: number
  order_id?: number
  order_no: string
  order_time: string
  order_status: string
  payment_status: string
  total_amount: number | string
  earned_points: number
  receiver_name: string
  receiver_phone: string
  receiver_address: string
  items?: Array<{
    product_name_snapshot: string
    unit_price: number | string
    quantity: number
    subtotal: number | string
  }>
}

export interface Message {
  id: number
  message_id?: number
  title: string
  content: string
  message_status: string
  created_time: string
  reply_content?: string | null
}

export interface PageResult<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export const statusLabels: Record<string, string> = {
  W: '待付款',
  C: '待确认',
  P: '已确认',
  F: '已完成',
  X: '已取消',
  R: '售后处理中',
  D: '已退款',
  U: '未支付',
  S: '支付成功',
  F_PAYMENT: '支付失败',
  A: '已显示',
  H: '已隐藏',
}

export function labelForStatus(value: string) {
  return statusLabels[value] ?? value
}
