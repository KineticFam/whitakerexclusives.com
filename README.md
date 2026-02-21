# Whitaker Exclusives

Exclusive luxury real estate listings site for [Whitaker Realty](https://w-realty.com) — Fort Lauderdale's premier boutique firm.

**Live site:** [whitakerexclusives.com](https://whitakerexclusives.com)

## Setup

### 1. GitHub Pages Deployment

```bash
cd whitaker-exclusives
git init
git add -A
git commit -m "Initial commit"
git remote add origin git@github.com:YOUR_ORG/whitaker-exclusives.git
git push -u origin main
```

Then in GitHub repo Settings → Pages → Source: **main** branch, root (`/`).

Set custom domain to `whitakerexclusives.com` and enable HTTPS.

### 2. DNS

Add to your DNS provider:
- `CNAME` record: `whitakerexclusives.com` → `YOUR_ORG.github.io`
- Or use A records pointing to GitHub Pages IPs

### 3. Email Inbox Parser

The parser reads emails from `chad@whitakerexclusives.com` and manages listings:

**Prerequisites:** `gog` CLI configured for `chad@whitakerexclusives.com`

**Install LaunchAgent** (runs every 15 minutes):
```bash
cp scripts/com.whitaker.inbox-parser.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.whitaker.inbox-parser.plist
```

**Email commands:**
- Subject: `Add Listing` — adds a new listing (see format in inbox-parser.py)
- Subject: `Update Listing` — updates an existing listing
- Subject: `Delete Listing` — removes a listing

### 4. Manual Deploy
```bash
bash scripts/deploy.sh
```

## File Structure

```
├── index.html          # Landing page
├── listings.html       # All exclusive listings
├── listing.html        # Individual listing detail (uses ?id= param)
├── listings.json       # Listing data (managed by email parser)
├── css/style.css       # Styles
├── js/main.js          # Nav, animations
├── js/listings.js      # Listing rendering logic
├── images/             # Logo, favicon
├── photos/             # Listing photos (organized by listing ID)
└── scripts/            # Email parser, deploy script, LaunchAgent
```

## Tech

Pure HTML/CSS/JS — no frameworks, no build tools. Listings data lives in `listings.json` and is rendered client-side.
