import { chromium } from "playwright";
import fs from "fs";

const FEED_URL = "https://valentinguigon.substack.com/feed";
const OUT_PATH = "_data/substack_feed.xml";

const browser = await chromium.launch();
const page = await browser.newPage({
  userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
});

const resp = await page.goto(FEED_URL, { waitUntil: "networkidle" });
if (!resp) throw new Error("No response received from page.goto()");
if (!resp.ok()) throw new Error(`HTTP ${resp.status()} while fetching feed`);

const body = await resp.text();
await browser.close();

// Hard validation: must look like RSS/Atom/XML, not an interstitial HTML page
const head = body.slice(0, 800).toLowerCase();
if (!(head.includes("<?xml") || head.includes("<rss") || head.includes("<feed"))) {
  throw new Error("Fetch did not return RSS/Atom/XML (likely Cloudflare). Refusing to write/commit.");
}

fs.mkdirSync("_data", { recursive: true });
fs.writeFileSync(OUT_PATH, body, "utf8");
