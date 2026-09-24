// The app's own screens — what a visitor could open before clicking anything.

export interface RouteDef {
  path: string;
  title: string;
  auth?: boolean;
}

export const routes: RouteDef[] = [
  { path: "/", title: "Home" },
  { path: "/catalog/:category", title: "Catalog" },
  { path: "/product/:slug", title: "Product" },
  { path: "/cart", title: "Cart" },
  { path: "/checkout", title: "Checkout", auth: true },
  { path: "/account/orders", title: "Orders", auth: true },
  { path: "/account/orders/:id", title: "Order", auth: true },
  { path: "/admin/refunds", title: "Refunds", auth: true },
];

export function match(pathname: string): RouteDef | undefined {
  return routes.find((r) => {
    const re = new RegExp("^" + r.path.replace(/:[^/]+/g, "[^/]+") + "$");
    return re.test(pathname);
  });
}
