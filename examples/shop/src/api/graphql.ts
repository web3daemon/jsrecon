// Catalogue and reviews live behind a GraphQL gateway.

const gql = (parts: TemplateStringsArray) => parts.join("");

export const PRODUCT_QUERY = gql`
  query Product($slug: String!) {
    product(slug: $slug) { id title price stock images { url } }
  }
`;

export const SEARCH_QUERY = gql`
  query SearchProducts($q: String!, $after: String) {
    search(q: $q, after: $after) { edges { node { id title price } } pageInfo { endCursor } }
  }
`;

export const ADD_REVIEW = gql`
  mutation AddReview($productId: ID!, $stars: Int!, $text: String) {
    addReview(productId: $productId, stars: $stars, text: $text) { id }
  }
`;

export const STOCK_UPDATES = gql`
  subscription StockUpdates($productId: ID!) {
    stock(productId: $productId) { available }
  }
`;

export async function graphql<T>(query: string, variables: Record<string, unknown>): Promise<T> {
  const res = await fetch("/graphql", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  return (await res.json()).data as T;
}
