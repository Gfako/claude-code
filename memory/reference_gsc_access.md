---
name: GSC service account access
description: Google Search Console is accessible via service account JSON at .credentials/gsc-service-account.json, property sc-domain:synthesia.io
type: reference
---

GSC service account JSON: `/Users/george.fakorellis/Desktop/SEO Custom Projects/.credentials/gsc-service-account.json`
GSC property: `sc-domain:synthesia.io`
Client email: `googlesearchconsole-georgefako@abstract-tract-491411-u4.iam.gserviceaccount.com`

Use `google.oauth2.service_account.Credentials` + `googleapiclient.discovery.build('searchconsole', 'v1')` to authenticate.
The content-brief skill pulls GSC data automatically when an existing page URL is provided.
A reusable script exists at `/Users/george.fakorellis/Desktop/SEO Custom Projects/gsc_pull.py`.
