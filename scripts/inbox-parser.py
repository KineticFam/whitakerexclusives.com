#!/usr/bin/env python3
"""
Whitaker Exclusives — Email Inbox Parser
Reads emails from chad@whitakerexclusives.com via gog CLI.
Handles Add/Update/Delete listing commands, updates listings.json, and deploys.
"""

import json
import os
import re
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Config
ACCOUNT = "chad@whitakerexclusives.com"
REPO_DIR = Path(__file__).resolve().parent.parent
LISTINGS_FILE = REPO_DIR / "listings.json"
PHOTOS_DIR = REPO_DIR / "photos"

def run(cmd, **kwargs):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(REPO_DIR), **kwargs)
    return result.stdout.strip(), result.returncode

def load_listings():
    if LISTINGS_FILE.exists():
        return json.loads(LISTINGS_FILE.read_text())
    return []

def save_listings(listings):
    LISTINGS_FILE.write_text(json.dumps(listings, indent=2) + "\n")

def generate_id(address):
    """Generate a URL-safe ID from an address."""
    clean = re.sub(r'[^a-z0-9\s]', '', address.lower())
    return re.sub(r'\s+', '-', clean.strip())

def parse_field(body, field_name):
    """Extract a field value from email body like 'Field: value'."""
    pattern = rf'^{re.escape(field_name)}\s*:\s*(.+)$'
    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_listing_from_body(body):
    """Parse all listing fields from an Add Listing email body."""
    listing = {}

    field_map = {
        'address': ('address', str),
        'city': ('city', str),
        'state': ('state', str),
        'zip': ('zip', str),
        'price': ('price', lambda x: int(re.sub(r'[^\d]', '', x))),
        'beds': ('beds', int),
        'baths': ('baths', lambda x: float(x) if '.' in x else int(x)),
        'sqft': ('sqft', lambda x: int(re.sub(r'[^\d]', '', x))),
        'year built': ('yearBuilt', int),
        'lot size': ('lotSize', str),
        'mls': ('mlsNumber', str),
        'agent': ('agent', str),
    }

    for email_field, (json_key, converter) in field_map.items():
        val = parse_field(body, email_field)
        if val:
            try:
                listing[json_key] = converter(val)
            except (ValueError, TypeError):
                listing[json_key] = val

    # Description (may be multi-line)
    desc_match = re.search(r'^Description\s*:\s*(.+?)(?=^Features\s*:|^$|\Z)', body, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if desc_match:
        listing['description'] = desc_match.group(1).strip()

    # Features (comma-separated)
    features = parse_field(body, 'features')
    if features:
        listing['features'] = [f.strip() for f in features.split(',') if f.strip()]

    # Defaults
    listing.setdefault('city', 'Fort Lauderdale')
    listing.setdefault('state', 'FL')
    listing.setdefault('agent', 'Chad Whitaker')

    return listing

def find_listing(listings, identifier):
    """Find a listing by address (fuzzy) or MLS number."""
    identifier = identifier.strip().lower()
    for l in listings:
        if l.get('mlsNumber', '').lower() == identifier:
            return l
        if l.get('address', '').lower() == identifier:
            return l
    # Fuzzy: check if identifier is contained in address
    for l in listings:
        if identifier in l.get('address', '').lower():
            return l
        if identifier in l.get('mlsNumber', '').lower():
            return l
    return None

def extract_identifier(body):
    """Extract the listing identifier (address or MLS) from first line or field."""
    # Check for explicit fields first
    addr = parse_field(body, 'address')
    if addr:
        return addr
    mls = parse_field(body, 'mls')
    if mls:
        return mls
    # Fall back to first non-empty line
    for line in body.strip().split('\n'):
        line = line.strip()
        if line:
            return line
    return None

def download_attachments(msg_id, listing_id):
    """Download email attachments to photos/listing-id/ directory."""
    photo_dir = PHOTOS_DIR / listing_id
    photo_dir.mkdir(parents=True, exist_ok=True)

    # Use gog to save attachments
    out, rc = run(f'gog mail attachments --account {ACCOUNT} --message-id "{msg_id}" --output-dir "{photo_dir}"')
    if rc != 0:
        print(f"  Warning: Could not download attachments: {out}")
        return []

    # Collect photo paths (relative to repo root)
    photos = []
    if photo_dir.exists():
        for f in sorted(photo_dir.iterdir()):
            if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
                photos.append(f"photos/{listing_id}/{f.name}")
    return photos

def send_confirmation(to, subject, body_text):
    """Send a confirmation email via gog."""
    escaped_body = body_text.replace('"', '\\"')
    run(f'gog mail send --account {ACCOUNT} --to "{to}" --subject "{subject}" --body "{escaped_body}"')

def git_deploy(action, address):
    """Commit and push listings.json."""
    msg = f"Listing update: {action} {address}"
    run('git add listings.json photos/')
    run(f'git commit -m "{msg}"')
    out, rc = run('git push')
    if rc != 0:
        print(f"  Warning: git push failed: {out}")
    else:
        print(f"  Deployed: {msg}")

def label_processed(msg_id):
    """Label email as processed so we don't re-process it."""
    run(f'gog mail label --account {ACCOUNT} --message-id "{msg_id}" --add "processed"')

def get_unprocessed_emails():
    """Fetch unread emails that aren't labeled 'processed'."""
    out, rc = run(f'gog mail list --account {ACCOUNT} --label INBOX --exclude-label processed --format json')
    if rc != 0 or not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print(f"  Warning: Could not parse email list: {out[:200]}")
        return []

def get_email(msg_id):
    """Fetch a single email's full content."""
    out, rc = run(f'gog mail read --account {ACCOUNT} --message-id "{msg_id}" --format json')
    if rc != 0 or not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None

def process_add(email_data, listings):
    """Handle an Add Listing email."""
    body = email_data.get('body', '')
    msg_id = email_data.get('id', '')
    sender = email_data.get('from', '')

    listing = parse_listing_from_body(body)
    if not listing.get('address'):
        print("  Error: No address found in Add Listing email")
        return False

    listing_id = generate_id(listing['address'])
    listing['id'] = listing_id
    listing['status'] = 'active'
    listing['addedDate'] = datetime.now().strftime('%Y-%m-%d')
    listing['photos'] = []

    # Download attached photos
    if msg_id:
        photos = download_attachments(msg_id, listing_id)
        listing['photos'] = photos

    # Check for duplicate
    existing = find_listing(listings, listing['address'])
    if existing:
        print(f"  Listing already exists: {listing['address']}. Updating instead.")
        existing.update(listing)
    else:
        listings.append(listing)

    save_listings(listings)
    git_deploy('add', listing['address'])
    send_confirmation(sender, f"Listing Added: {listing['address']}",
                      f"Your listing at {listing['address']} has been added to whitakerexclusives.com.\n\nPrice: ${listing.get('price', 'N/A'):,}\nStatus: Active")
    print(f"  Added: {listing['address']}")
    return True

def process_update(email_data, listings):
    """Handle an Update Listing email."""
    body = email_data.get('body', '')
    sender = email_data.get('from', '')

    identifier = extract_identifier(body)
    if not identifier:
        print("  Error: No identifier found in Update Listing email")
        return False

    listing = find_listing(listings, identifier)
    if not listing:
        print(f"  Error: Listing not found: {identifier}")
        send_confirmation(sender, "Update Failed", f"Could not find listing matching: {identifier}")
        return False

    # Parse update fields
    updates = parse_listing_from_body(body)
    # Remove empty/None values
    updates = {k: v for k, v in updates.items() if v is not None and v != ''}
    # Don't override id/status/photos unless explicit
    updates.pop('id', None)

    listing.update(updates)
    save_listings(listings)
    git_deploy('update', listing['address'])
    send_confirmation(sender, f"Listing Updated: {listing['address']}",
                      f"Your listing at {listing['address']} has been updated on whitakerexclusives.com.\n\nUpdated fields: {', '.join(updates.keys())}")
    print(f"  Updated: {listing['address']}")
    return True

def process_delete(email_data, listings):
    """Handle a Delete Listing email."""
    body = email_data.get('body', '')
    sender = email_data.get('from', '')

    identifier = extract_identifier(body)
    if not identifier:
        print("  Error: No identifier found in Delete Listing email")
        return False

    listing = find_listing(listings, identifier)
    if not listing:
        print(f"  Error: Listing not found: {identifier}")
        send_confirmation(sender, "Delete Failed", f"Could not find listing matching: {identifier}")
        return False

    address = listing['address']
    listing_id = listing['id']
    listings.remove(listing)

    # Remove photos directory
    photo_dir = PHOTOS_DIR / listing_id
    if photo_dir.exists():
        shutil.rmtree(photo_dir)

    save_listings(listings)
    git_deploy('delete', address)
    send_confirmation(sender, f"Listing Deleted: {address}",
                      f"The listing at {address} has been removed from whitakerexclusives.com.")
    print(f"  Deleted: {address}")
    return True

def main():
    print(f"[{datetime.now().isoformat()}] Checking inbox...")

    emails = get_unprocessed_emails()
    if not emails:
        print("  No new emails to process.")
        return

    listings = load_listings()
    processed_count = 0

    for email_summary in emails:
        msg_id = email_summary.get('id', '')
        subject = email_summary.get('subject', '').strip().lower()

        if not any(cmd in subject for cmd in ['add listing', 'update listing', 'delete listing']):
            continue

        email_data = get_email(msg_id)
        if not email_data:
            print(f"  Could not read email {msg_id}")
            continue

        email_data['id'] = msg_id
        email_data['from'] = email_summary.get('from', '')

        print(f"  Processing: {email_summary.get('subject', '')}")

        success = False
        if 'add listing' in subject:
            success = process_add(email_data, listings)
        elif 'update listing' in subject:
            success = process_update(email_data, listings)
        elif 'delete listing' in subject:
            success = process_delete(email_data, listings)

        if success:
            processed_count += 1

        # Always label as processed to avoid re-processing
        label_processed(msg_id)

    print(f"  Done. Processed {processed_count} listing email(s).")

if __name__ == '__main__':
    main()
