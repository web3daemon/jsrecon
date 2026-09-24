const API = "https://api.example.com/v2";
async function load(id) { const r = await fetch(`${API}/users/${id}`); return r.json(); }
export const getUsers = () => fetch("/api/users");
axios.post("/api/orders", { qty: 1 });
fetch("/v1/session", { method: "POST" });
const q = `query GetUser($id: ID!) { user(id: $id) { name email } }`;
const cfg = { awsKey: "AKIAIOSFODNN7EXAMPLE", flag_new_ui: true };
//# sourceMappingURL=app.js.map
