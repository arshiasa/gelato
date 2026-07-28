addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

// Specific menu API URLs for the two branches discovered from browser network traffic
const BRANCH_API_URLS = {
  "gelatohouse": "https://restaurant.delino.com/restaurant/menu/252983dd-4fce-4433-b9b0-793651952666", // Shahrak Gharb
  "gelato-house": "https://restaurant.delino.com/restaurant/menu/b80e90fa-0155-41a5-a01c-633db20aad12" // Velenjak
}

async function checkAvailability(branchCode) {
  const targetUrl = BRANCH_API_URLS[branchCode]
  if (!targetUrl) {
    return {
      available: false,
      error: `Unknown branch code: ${branchCode}`,
      url: null,
      length: 0,
      snippet: ""
    }
  }

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'fa,en;q=0.9'
      }
    })
    
    if (!response.ok) {
      return { 
        available: false, 
        error: `HTTP status ${response.status} from API`,
        url: targetUrl,
        length: 0,
        snippet: ""
      }
    }
    
    const text = await response.text()
    // Checks if the branch menu JSON contains 'پشن'
    const isAvailable = text.includes('پشن') || text.includes('passion')
    
    return {
      available: isAvailable,
      error: null,
      url: targetUrl,
      length: text.length,
      snippet: text.slice(0, 300)
    }
  } catch (err) {
    return {
      available: false,
      error: err.message,
      url: targetUrl,
      length: 0,
      snippet: ""
    }
  }
}

async function handleRequest(request) {
  const url = new URL(request.url)
  const path = url.pathname.toLowerCase().replace(/\/$/, "") // remove trailing slash
  
  // If ?json=true is provided, return availability JSON. Otherwise, act as a transparent proxy.
  const isJsonRequest = url.searchParams.get("json") === "true"
  
  let branchCode = ""
  if (path === "/order/gelatohouse") {
    branchCode = "gelatohouse"
  } else if (path === "/order/gelato-house") {
    branchCode = "gelato-house"
  }
  
  // 1. JSON status check path requested by Python script
  if (branchCode && isJsonRequest) {
    const result = await checkAvailability(branchCode)
    return new Response(JSON.stringify(result), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      }
    })
  }
  
  // 2. Otherwise, behave as a transparent proxy to order.gelatohouse.ir (using HTTPS)
  // This allows the browser to visit the website normally without getting raw JSON.
  try {
    const targetUrl = `https://order.gelatohouse.ir${url.pathname}${url.search}`
    
    // We rewrite headers to avoid Host validation errors on target server
    const headers = new Headers(request.headers)
    headers.set('Host', 'order.gelatohouse.ir')
    headers.set('Origin', 'https://order.gelatohouse.ir')
    headers.set('Referer', 'https://order.gelatohouse.ir/')
    
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined
    })
    
    return response
  } catch (err) {
    return new Response(`Proxy Error: ${err.message}`, { status: 500 })
  }
}
