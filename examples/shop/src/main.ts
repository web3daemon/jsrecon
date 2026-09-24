import { trackView } from "./analytics";
import { addToCart, applyCoupon, checkoutSession } from "./api/cart";
import { ADD_REVIEW, PRODUCT_QUERY, SEARCH_QUERY, STOCK_UPDATES, graphql } from "./api/graphql";
import { cancelOrder, createOrder, getOrder, listOrders, refundOrder } from "./api/orders";
import { login, logout, me, updateProfile } from "./api/users";
import { S3_UPLOAD_KEY } from "./config";
import { match } from "./router";

// Everything the pages call, exposed for the demo so the bundler keeps it.
const actions = {
  me, updateProfile, login, logout,
  listOrders, getOrder, createOrder, cancelOrder, refundOrder,
  addToCart, applyCoupon, checkoutSession,
  product: (slug: string) => graphql(PRODUCT_QUERY, { slug }),
  search: (q: string) => graphql(SEARCH_QUERY, { q }),
  review: (productId: string, stars: number) => graphql(ADD_REVIEW, { productId, stars }),
  stock: STOCK_UPDATES,
  uploadKey: S3_UPLOAD_KEY,
};

function render() {
  const route = match(location.pathname);
  document.title = route ? `${route.title} · Shop` : "Not found · Shop";
  document.querySelector("#app")!.textContent = route?.title ?? "404";
  trackView(location.pathname);
}

(window as unknown as { shop: typeof actions }).shop = actions;
addEventListener("popstate", render);
render();
