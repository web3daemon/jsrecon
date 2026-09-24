// Fire-and-forget page-view beacon; old-school XHR so it works in every webview.

export function trackView(route: string) {
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/events/pageview");
  xhr.setRequestHeader("content-type", "application/json");
  xhr.send(JSON.stringify({ route, at: Date.now() }));
}
