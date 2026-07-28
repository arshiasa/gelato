# Handover Documentation: Gelato House Monitor

This document outlines the purpose, architecture, development history, and deployment instructions for the Gelato House Passion Fruit availability monitor.

---

## 1. Purpose & Scope
The objective is to automatically track the availability of **Passion Fruit (پشن فروت)** gelato at two Gelato House branches:
* **Shahrak Gharb (شهرک غرب)**: `http://order.gelatohouse.ir/order/gelatohouse`
* **Velenjak (ولنجک)**: `http://order.gelatohouse.ir/order/gelato-house`

When availability changes (e.g., from out-of-stock to in-stock or vice versa), the system must:
1. Send an immediate Telegram notification to target chat IDs.
2. Update a public status dashboard (`index.html`) hosted on GitHub Pages.

---

## 2. System Architecture

The project consists of three main components:

```mermaid
graph TD
    subgraph GitHub Actions Runner (Global IP)
        M[monitor.py] -->|1. Request JSON Status| W[Arvan Edge Worker]
        M -->|3. Commit changes| S[state.json]
        M -->|4. Trigger Alert| T[Telegram API]
        D[index.html] -->|Reads status| S
    end

    subgraph Arvan Cloud (Iranian IP)
        W -->|2a. Query API/HTML| GH[order.gelatohouse.ir / Delino]
        GH -->|2b. Return Data| W
    end
```

### 1. Arvan Edge Worker (`worker.js`)
* **Role**: Network bridge and parser.
* **Why**: The target server (`order.gelatohouse.ir` / Delino backend) is heavily geo-fenced and blocks all requests from outside Iran, including GitHub Actions and major cloud hosting providers.
* **Function**: Runs on Arvan Cloud (inside Iran). It exposes two endpoints:
  * `/order/gelatohouse?json=true` (Shahrak Gharb)
  * `/order/gelato-house?json=true` (Velenjak)
  *(Without `?json=true`, the worker behaves as a transparent HTML proxy so that users can browse the Gelato House website normally through it).*
* **Scraping logic**: It attempts to query the backend Delino APIs directly via HTTPS, falling back to HTTPS page HTML, and searches for the keyword `پشن` (Persian for "Passion"). It returns a simple JSON availability response:
  ```json
  {
    "available": true,
    "error": null,
    "url": "https://restaurant.delino.com/api/restaurant/menu?code=gelatohouse",
    "length": 45102,
    "snippet": "..."
  }
  ```

### 2. Monitor Script (`monitor.py`)
* **Role**: State manager and notifier.
* **Function**: Runs inside GitHub Actions on a schedule. It queries the two endpoints on your Arvan Worker, checks the response for `available`, compares the results against the cached status in `state.json`, and fires Telegram alerts if there are state changes.

### 3. Dashboard (`index.html`)
* **Role**: Frontend representation.
* **Function**: A pastel-themed single-page status board hosted on GitHub Pages. It loads `state.json` and renders status cards.
* **Special feature**: Includes an HTML5 Canvas-based background renderer to bypass Android/Chrome "forced dark mode" text/background color inversions.

---

## 3. History of Attempts (What Worked vs. What Didn't)

### What DID NOT Work:
* **Direct scraping from GitHub Actions**: Timed out due to the Iranian national firewall geo-blocking foreign IP ranges.
* **Public Iranian Proxies**: 100% of free proxies scraped from GeoNode and public lists timed out or returned block pages due to severe filtering and instability.
* **Foreign Cloud Hosting (Doprax/Heroku)**: Blocked by the firewall because they use foreign hosting networks (Hetzner, AWS, etc.).
* **Pure HTTP Requests**: Requests to `http://order.gelatohouse.ir` hung and timed out. The target server drops port 80 traffic entirely, only responding to port 443 (HTTPS).
* **HTML Scraping directly**: Gelato House is a Single Page React Application (white-labeled by Delino). Fetching the raw page HTML only returns a static `9KB` React shell containing script tags. Product details like "پشن فروت" are not present in the HTML; they are fetched dynamically via client-side API requests.

### What Worked:
* **Edge Proxying inside Iran**: Deploying a serverless JS worker on Arvan Cloud (Iranian IP network) successfully bypasses the firewall and reaches the backend.
* **Internal Scraping**: Performing the fetch and search logic completely inside the Arvan Worker (instead of sending raw HTML back to GitHub Actions) eliminates payload size overhead and avoids connection timeouts.

---

Both the `main` and `pastel-theme` branches are fully synchronized. The exact API endpoints for both branches are configured in the worker code.

### Step 1: Deploy the Worker Code
Paste the contents of `worker.js` into your Arvan Cloud Worker panel. Ensure it is deployed to your worker domain (e.g. `gelato.arshiasalimi2002-3orjs.arvanedge.ir`).

### Step 2: Verify the Status Check
Once the worker is deployed, trigger the GitHub Actions workflow manually (or wait for the 5-minute cron schedule). 
Check the generated `state.json` file in your repository. It will show the correct status (`true` or `false`) fetched directly from the JSON menus:
* **Velenjak API URL**: `https://restaurant.delino.com/restaurant/menu/b80e90fa-0155-41a5-a01c-633db20aad12`
* **Shahrak Gharb API URL**: `https://restaurant.delino.com/restaurant/menu/252983dd-4fce-4433-b9b0-793651952666`
