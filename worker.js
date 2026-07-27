addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const targetPath = url.pathname + url.search
  const targetUrl = `http://order.gelatohouse.ir${targetPath}`

  const proxyRequest = new Request(targetUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body,
    redirect: 'manual'
  })

  proxyRequest.headers.set('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

  try {
    const response = await fetch(proxyRequest)
    const proxyResponse = new Response(response.body, response)
    proxyResponse.headers.set('Access-Control-Allow-Origin', '*')
    return proxyResponse
  } catch (err) {
    return new Response(`Proxy Error: ${err.message}`, { status: 502 })
  }
}
