// The cart talks to the storefront edge directly, not through `api`.

export async function addToCart(productId: string, qty = 1) {
  const res = await fetch("/api/cart/items", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ productId, qty }),
  });
  return res.json();
}

export function applyCoupon(code: string) {
  return fetch("/api/cart/coupon", { method: "PUT", body: JSON.stringify({ code }) });
}

export function checkoutSession() {
  return fetch("https://pay.example.com/v1/checkout/sessions", { method: "POST", credentials: "include" });
}
