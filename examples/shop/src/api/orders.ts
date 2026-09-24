import { api } from "./client";

export interface Order {
  id: string;
  status: "pending" | "paid" | "shipped";
  total: number;
}

export const listOrders = (page = 1) => api.get<Order[]>(`/orders?page=${page}`);

export const getOrder = (id: string) => api.get<Order>(`/orders/${id}`);

export const createOrder = (cartId: string) => api.post<Order>("/orders", { cartId });

export const cancelOrder = (id: string) => api.delete<void>(`/orders/${id}`);

export const refundOrder = (id: string, reason: string) =>
  api.post<Order>(`/orders/${id}/refund`, { reason });
