# Response Header Comparison

## Python implementation (labs-beta)

URL: `https://labs-beta.waterdata.usgs.gov/api/nldi/linked-data/comid/21412883/navigation/UM/flowlines?distance=10&f=json`
Date: 2026-03-30

### HEAD request (405 — not supported)
```
HTTP/2 405
content-type: application/json
content-length: 49
date: Mon, 30 Mar 2026 18:07:13 GMT
strict-transport-security: max-age=31536000; includeSubDomains; preload
server: nginx
allow: GET, OPTIONS
x-cache: Error from cloudfront
via: 1.1 985074e151de212b5f396dd486390986.cloudfront.net (CloudFront)
x-amz-cf-pop: MSP50-P4
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
referrer-policy: origin-when-cross-origin
x-content-type-options: nosniff
```

### GET request #1 (cache miss)
```
HTTP/2 200
content-type: application/json
date: Mon, 30 Mar 2026 18:09:28 GMT
x-xss-protection: 1; mode=block
strict-transport-security: max-age=31536000; includeSubDomains; preload
server: nginx
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
vary: Accept-Encoding
x-cache: Miss from cloudfront
via: 1.1 031ecdfc38254766d2c525e7f1898d84.cloudfront.net (CloudFront)
x-amz-cf-pop: MSP50-P4
referrer-policy: origin-when-cross-origin
```

### GET request #2 (cache hit)
```
HTTP/2 200
content-type: application/json
date: Mon, 30 Mar 2026 18:09:28 GMT
x-xss-protection: 1; mode=block
strict-transport-security: max-age=31536000; includeSubDomains; preload
server: nginx
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
vary: Accept-Encoding
x-cache: Hit from cloudfront
via: 1.1 f36b0870f87c066f89a9b16619a41004.cloudfront.net (CloudFront)
x-amz-cf-pop: MSP50-P4
age: 17
referrer-policy: origin-when-cross-origin
```

### Notable observations
- No `Cache-Control` header — CloudFront using its own default TTL
- No `Access-Control-Allow-Origin` — CORS headers completely absent
- `Vary: Accept-Encoding` only (from nginx, not the app)
- No `Content-Length` (streaming/chunked response)
- HEAD returns 405

---

## Java implementation (production)

URL: `https://api.water.usgs.gov/nldi/linked-data/comid/21412883/navigation/UM/flowlines?distance=10&f=json`
Date: 2026-03-30

### HEAD request (200 — supported!)
```
HTTP/2 200
date: Mon, 30 Mar 2026 18:31:49 GMT
content-type: application/vnd.geo+json
content-length: 7077
age: 0
cache-control: no-cache, no-store, max-age=0, must-revalidate
expires: 0
pragma: no-cache
referrer-policy: origin-when-cross-origin
set-cookie: XSRF-TOKEN=245ea675-5acb-4c6a-8c5f-63c5612986dd; Path=/nldi
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 3caf9df4ca497afd40efb87f8957a7fa.cloudfront.net (CloudFront), https/1.1 api-umbrella (ApacheTrafficServer [cMsSf ])
x-amz-cf-pop: HIO52-P4
x-api-umbrella-request-id: ct80233htothindvt270
x-cache: Miss from cloudfront
x-content-type-options: nosniff
x-ratelimit-limit: 1000
x-ratelimit-remaining: 996
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
```

### GET request #1 (cache miss)
```
HTTP/2 200
date: Mon, 30 Mar 2026 18:32:00 GMT
content-type: application/vnd.geo+json
age: 0
cache-control: no-cache, no-store, max-age=0, must-revalidate
expires: 0
pragma: no-cache
referrer-policy: origin-when-cross-origin
set-cookie: XSRF-TOKEN=5669e94a-fbdd-497b-a00c-e77f982745a5; Path=/nldi
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 38789cdd14ddea5c4c609cb0e6656396.cloudfront.net (CloudFront), https/1.1 api-umbrella (ApacheTrafficServer [cMsSf ])
x-amz-cf-pop: HIO52-P4
x-api-umbrella-request-id: ct8025mcluk9249kr730
x-cache: Miss from cloudfront
x-content-type-options: nosniff
x-ratelimit-limit: 1000
x-ratelimit-remaining: 995
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
```

### GET request #2 (cache hit)
```
HTTP/2 200
date: Mon, 30 Mar 2026 18:32:13 GMT
content-type: application/vnd.geo+json
age: 13
cache-control: no-cache, no-store, max-age=0, must-revalidate
expires: 0
pragma: no-cache
referrer-policy: origin-when-cross-origin
set-cookie: XSRF-TOKEN=5669e94a-fbdd-497b-a00c-e77f982745a5; Path=/nldi
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 5ec2b95241693f962e2ff4afc726b38e.cloudfront.net (CloudFront), https/1.1 api-umbrella (ApacheTrafficServer [cMsSf ])
x-amz-cf-pop: HIO52-P4
x-api-umbrella-request-id: ct8028susm0s42qthip0
x-cache: Hit from cloudfront
x-content-type-options: nosniff
x-ratelimit-limit: 1000
x-ratelimit-remaining: 994
x-xss-protection: 1; mode=block
x-frame-options: SAMEORIGIN
```

### Notable observations
- HEAD returns 200 (Spring Boot handles HEAD for GET routes automatically)
- `content-type: application/vnd.geo+json` (not `application/json`)
- `content-length: 7077` present (not chunked/streaming)
- `cache-control: no-cache, no-store, max-age=0, must-revalidate` — explicitly tells clients NOT to cache
- CloudFront caches anyway (age: 13 on hit) — CF is ignoring the app's cache headers
- No `Access-Control-Allow-Origin` either — same CORS gap as Python version
- No `Vary` header at all
- Has `set-cookie: XSRF-TOKEN` — Spring Security default
- Has rate limiting headers (`x-ratelimit-*`) via api-umbrella
- Extra proxy layer: api-umbrella (ApacheTrafficServer) between CloudFront and origin

---

## Key Differences: Python vs Java

| Header | Python (labs-beta) | Java (production) |
|--------|-------------------|-------------------|
| Content-Type | `application/json` | `application/vnd.geo+json` |
| Content-Length | absent (streaming) | present (7077) |
| Cache-Control | absent | `no-cache, no-store, max-age=0` |
| Vary | `Accept-Encoding` (nginx) | absent |
| CORS headers | absent | absent |
| HEAD support | 405 | 200 |
| XSRF cookie | no | yes |
| Rate limiting | no | yes (api-umbrella) |
