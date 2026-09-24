function c(t){let e=new XMLHttpRequest;e.open("POST","/api/events/pageview"),e.setRequestHeader("content-type","application/json"),e.send(JSON.stringify({route:t,at:Date.now()}))}async function p(t,e=1){return(await fetch("/api/cart/items",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({productId:t,qty:e})})).json()}function d(t){return fetch("/api/cart/coupon",{method:"PUT",body:JSON.stringify({code:t})})}function u(){return fetch("https://pay.example.com/v1/checkout/sessions",{method:"POST",credentials:"include"})}var n=t=>t.join(""),g=n`
  query Product($slug: String!) {
    product(slug: $slug) { id title price stock images { url } }
  }
`,l=n`
  query SearchProducts($q: String!, $after: String) {
    search(q: $q, after: $after) { edges { node { id title price } } pageInfo { endCursor } }
  }
`,h=n`
  mutation AddReview($productId: ID!, $stars: Int!, $text: String) {
    addReview(productId: $productId, stars: $stars, text: $text) { id }
  }
`,f=n`
  subscription StockUpdates($productId: ID!) {
    stock(productId: $productId) { available }
  }
`;async function s(t,e){return(await(await fetch("/graphql",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:t,variables:e})})).json()).data}var m="https://api.example.com/v2";var S="AKIAIOSFODNN7EXAMPLE";async function i(t,e,o){let a=await fetch(m+e,{method:t,credentials:"include",headers:o?{"content-type":"application/json"}:void 0,body:o?JSON.stringify(o):void 0,signal:AbortSignal.timeout(3e4)});if(!a.ok)throw new Error(`${t} ${e} \u2192 ${a.status}`);return a.json()}var r={get:t=>i("GET",t),post:(t,e)=>i("POST",t,e),put:(t,e)=>i("PUT",t,e),delete:t=>i("DELETE",t)};var T=(t=1)=>r.get(`/orders?page=${t}`),O=t=>r.get(`/orders/${t}`),x=t=>r.post("/orders",{cartId:t}),E=t=>r.delete(`/orders/${t}`),y=(t,e)=>r.post(`/orders/${t}/refund`,{reason:e});var P=()=>r.get("/users/me"),R=t=>r.put("/users/me",t),$=(t,e)=>fetch("/auth/session",{method:"POST",credentials:"include",body:JSON.stringify({email:t,password:e})}),U=()=>fetch("/auth/session",{method:"DELETE",credentials:"include"});var A=[{path:"/",title:"Home"},{path:"/catalog/:category",title:"Catalog"},{path:"/product/:slug",title:"Product"},{path:"/cart",title:"Cart"},{path:"/checkout",title:"Checkout",auth:!0},{path:"/account/orders",title:"Orders",auth:!0},{path:"/account/orders/:id",title:"Order",auth:!0},{path:"/admin/refunds",title:"Refunds",auth:!0}];function w(t){return A.find(e=>new RegExp("^"+e.path.replace(/:[^/]+/g,"[^/]+")+"$").test(t))}var I={me:P,updateProfile:R,login:$,logout:U,listOrders:T,getOrder:O,createOrder:x,cancelOrder:E,refundOrder:y,addToCart:p,applyCoupon:d,checkoutSession:u,product:t=>s(g,{slug:t}),search:t=>s(l,{q:t}),review:(t,e)=>s(h,{productId:t,stars:e}),stock:f,uploadKey:S};function D(){let t=w(location.pathname);document.title=t?`${t.title} \xB7 Shop`:"Not found \xB7 Shop",document.querySelector("#app").textContent=t?.title??"404",c(location.pathname)}window.shop=I;addEventListener("popstate",D);D();
//# sourceMappingURL=main-RU4RXFFD.js.map
