# Source review — Checkpoint 1

Reviewed: 2026-10-26 (Asia/Kolkata). Category requested: skincare / personal care. Requested source type: Indian brand's own online store. Mamaearth is approved by the user for a personal portfolio project under the specific limits recorded below. Plum and Minimalist were not selected. robots.txt is not permission; the user's approval is limited to the scope stated in the Mamaearth entry.

The page checks below used a small set of public storefront, robots.txt, terms, and product-page reads. The web retrieval view exposed page text but not raw response headers or source markup. Where noted, JSON-LD presence and a live browser's post-JavaScript DOM were not independently verified. One retrieval may be cached; see each product evidence note. Current promotions show that offers are visible at the time/content of review; one review cannot establish a regular sale cadence.

## Candidate 1 — Minimalist

- **Name / site:** Minimalist — [beminimalist.co](https://beminimalist.co/)
- **Date reviewed:** 2026-10-26
- **Robots.txt:** [beminimalist.co/robots.txt](https://beminimalist.co/robots.txt) has `User-agent: *`, `Allow: /`, and disallows administrative, cart, checkout, order, account, service, and recommendation paths. No product-path disallow or `Crawl-delay` was found in the checked file. Robots is not permission.
- **Terms:** [Terms of Use, section 4.2](https://beminimalist.co/pages/terms). The clause says site information and intellectual property may not be copied, downloaded, transmitted, stored for later use, or otherwise used without prior written consent. Relevant excerpt: “without the prior written consent of Minimalist.” The page does not specifically discuss automated access in the checked text; its content-use restriction is relevant and requires the user's decision. This is not legal advice.
- **Official API/feed:** No general-purpose public price API or affiliate feed was located in the pages checked. No API availability is claimed either way beyond that limited review.
- **Public product pricing:** The public [Niacinamide 10% Face Serum page](https://beminimalist.co/products/niacinamide-10-with-matmarine) showed 30 ml at ₹569 with MRP ₹599 crossed out, without a login. Other variants were displayed separately. The retrieved page text was dated as crawled four months earlier by the retrieval service, so treat the displayed price as evidence of page format, not a current price quote.
- **Markup / JavaScript:** Price and MRP appeared in the retrieved HTML page text; they were not available only after an identified login. The retrieval did not expose raw HTML tags, so JSON-LD presence and whether a live browser adds or changes values with JavaScript remain unverified.
- **Sales:** Current/retrieved storefront content included offer messaging (for example, multi-buy/free-item offers) and the product's reduced price versus MRP. Regular sale frequency is unverified.
- **Access method / limits:** Public storefront GET-style page reads only; no login or checkout. No source-specific crawl delay was found. Do not proceed without the user's explicit approval and any required permission for content use.
- **Decision:** **not selected (fallback: Plum, then Minimalist)**

## Candidate 2 — Plum Goodness

- **Name / site:** Plum Goodness — [plumgoodness.com](https://plumgoodness.com/)
- **Date reviewed:** 2026-10-26
- **Robots.txt:** [plumgoodness.com/robots.txt](https://plumgoodness.com/robots.txt) has `User-agent: *` and `Allow: /`; product pages are not disallowed for that group. It disallows admin, cart, checkout, orders, accounts, service/AJAX, recommendations, and selected crawl-trap paths. No `Crawl-delay` was found. The file also lists a UCP discovery URL and UCP/MCP endpoint; those are not assumed to be a price feed. Robots is not permission.
- **Terms:** [Terms & Conditions](https://plumgoodness.com/pages/terms-conditions), especially “Ownership of rights.” It says use/copying/storing beyond personal, non-commercial use is prohibited without explicit permission and also prohibits commercial exploitation of content. Relevant excerpt: “other than for your own personal, non-commercial use is prohibited without the explicit permission of Plum.” The checked terms do not specifically address automated access. This is not legal advice.
- **Official API/feed:** The robots file advertises `/.well-known/ucp` and `/api/ucp/mcp`, but I did not verify these as a general-purpose public price API/feed. No public affiliate price feed was located in the limited checks.
- **Public product pricing:** The public [Green Tea Alcohol-Free Toner page](https://plumgoodness.com/products/green-tea-alcohol-free-pore-tightening-face-toner-for-oily-acne-prone-skin-1?variant=40307956416572) returned ₹420 for the selected 200 ml variant, without a login; its main product block did not show an MRP crossed out alongside that price. The retrieved collection listing showed ₹336 and ₹420 (20% off) for the toner, but the product-page capture reported a ₹0 product discount and also displayed a cart-applied offer. The retrieval service dated the product capture about three weeks earlier, so the exact price may be stale.
- **Markup / JavaScript:** Product price was present in the retrieved HTML page text; it was not login-gated. JSON-LD presence and live-browser JavaScript effects were not verified because raw markup/DOM comparison was not available in the retrieval.
- **Sales:** The retrieved collection and product content showed discounts and limited-time/cart offers. A regular cadence is unverified.
- **Access method / limits:** Public storefront GET-style page reads only; no login or checkout. `robots.txt` lists public product paths as crawlable for `User-agent: *`, but the terms' explicit permission language still needs your decision. The UCP/MCP path should not be probed or used absent your approval and review of its terms.
- **Decision:** **not selected (fallback: Plum, then Minimalist)**

## Candidate 3 — Mamaearth

- **Name / site:** Mamaearth — [mamaearth.in](https://mamaearth.in/)
- **Date reviewed:** 2026-10-26
- **Robots.txt:** [mamaearth.in/robots.txt](https://mamaearth.in/robots.txt) has `User-agent: *` and `Allow: /`; product pages are not disallowed for that group. It disallows admin, cart, checkout, orders, accounts, service/AJAX, recommendations, and selected crawl-trap paths. No `Crawl-delay` was found. Like Plum, the file lists UCP discovery and UCP/MCP endpoint URLs; these were not tested as price feeds. Robots is not permission.
- **Terms:** [Terms & Conditions, License section](https://mamaearth.in/pages/terms-conditions). It grants a limited right for personal, non-commercial use and says copying or distributing site content requires express written authorization. Relevant excerpt: “without express written authorization from the Company.” The checked terms do not specifically mention automated access. This is not legal advice.
- **Official API/feed:** The robots file lists a UCP discovery file and UCP/MCP endpoint, but I did not verify a general-purpose public price API/feed. No public affiliate price feed was located in the limited checks.
- **Public product pricing:** The public [Ubtan Natural Glow Face Wash page](https://mamaearth.in/products/ubtan-face-wash-with-turmeric-saffron-for-tan-removal-150-ml) showed 150 ml at sale price ₹359 and MRP ₹449 crossed out, without login. Other variant prices appeared separately.
- **Markup / JavaScript:** Sale price and MRP appeared in the retrieved HTML page text; they were not login-gated. JSON-LD presence and live-browser JavaScript effects were not independently verified from raw markup.
- **Sales:** The terms page header and product/collection pages displayed Buy 1 Get 1 and percentage-off messaging. This establishes visible promotions in the retrieved pages, not a regular cadence.
- **Access method / limits:** Public storefront page reads only; no login or checkout. No source-specific crawl delay was found. Approved scope is about 10–15 public product pages, once a day, with polite rate limits and robots.txt respected; no logins or personal data. Raw observations remain private. Only code and aggregated results may be published. Stop if the site blocks access or asks the project to stop. The user accepts the terms-related risk for this personal portfolio project.
- **User approval note:** "Approved by me. Terms limit use to personal, non-commercial use; I accept this risk for a personal portfolio project. Low volume only: about 10-15 public product pages, once a day, polite rate limits, robots.txt respected, no logins, no personal data. Raw data stays private; only code and aggregated results are published. Will stop if the site blocks me or asks me to."
- **Decision:** **approved**

## Review outcome

Mamaearth is approved only for the user-stated personal portfolio scope above. Plum and Minimalist are not selected, in that fallback order. No source-specific scraper or selector has been written yet.

