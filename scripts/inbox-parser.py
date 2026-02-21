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
    desc_match = re.search(r'^Description\s*:\s*(.+?)(?=^Features\s*:|^Photos\s*:|^Photo Folder\s*:|^$|\Z)', body, re.MULTILINE | re.IGNORECASE | re.DOTALL)
    if desc_match:
        listing['description'] = desc_match.group(1).strip()

    # Features (comma-separated)
    features = parse_field(body, 'features')
    if features:
        listing['features'] = [f.strip() for f in features.split(',') if f.strip()]

    # Photos (Drive URLs)
    photos = []
    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('https://drive.google.com/uc?id='):
            photos.append(line)
    if photos:
        listing['photos'] = photos

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
    addr = parse_field(body, 'address')
    if addr:
        return addr
    mls = parse_field(body, 'mls')
    if mls:
        return mls
    for line in body.strip().split('\n'):
        line = line.strip()
        if line:
            return line
    return None

def send_confirmation(to, subject, body_text):
    """Send a confirmation email via gog."""
    escaped_body = body_text.replace("'", "'\\''")
    run(f"gog gmail send --account {ACCOUNT} --to '{to}' --subject '{subject}' --body '{escaped_body}'")

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

def ensure_processed_label():
    """Create 'processed' label if it doesn't exist."""
    out, _ = run(f'gog gmail labels list --account {ACCOUNT} --plain')
    if 'processed' not in out.lower():
        run(f'gog gmail labels create --account {ACCOUNT} processed')
        print("  Created 'processed' label")

def label_processed(thread_id):
    """Label thread as processed and remove from inbox."""
    run(f'gog gmail thread modify --account {ACCOUNT} --add processed --remove INBOX {thread_id}')

def get_emails():
    """Fetch emails matching listing commands, excluding already processed."""
    emails = []
    for subject_query in ['subject:"Add Listing"', 'subject:"Update Listing"', 'subject:"Delete Listing"']:
        query = f'{subject_query} -label:processed in:inbox'
        out, rc = run(f'gog gmail search --account {ACCOUNT} --json "{query}"')
        if rc != 0 or not out:
            continue
        try:
            results = json.loads(out)
            if isinstance(results, list):
                emails.extend(results)
            elif isinstance(results, dict) and 'threads' in results:
                emails.extend(results['threads'])
            elif isinstance(results, dict) and 'messages' in results:
                emails.extend(results['messages'])
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse search results for {subject_query}")
    return emails

def get_message(msg_id):
    """Fetch a single message's content."""
    out, rc = run(f'gog gmail get --account {ACCOUNT} --json {msg_id}')
    if rc != 0 or not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None

def process_add(msg_data, listings):
    """Handle an Add Listing email."""
    body = msg_data.get('body', '')
    sender = ''
    headers = msg_data.get('headers', {})
    if isinstance(headers, dict):
        sender = headers.get('From', headers.get('from', ''))
    elif isinstance(headers, list):
        for h in headers:
            if h.get('name', '').lower() == 'from':
                sender = h.get('value', '')
                break

    listing = parse_listing_from_body(body)
    if not listing.get('address'):
        print("  Error: No address found in Add Listing email")
        return False

    listing_id = generate_id(listing['address'])
    listing['id'] = listing_id
    listing['status'] = 'active'
    listing['addedDate'] = datetime.now().strftime('%Y-%m-%d')
    listing.setdefault('photos', [])

    # Check for duplicate
    existing = find_listing(listings, listing['address'])
    if existing:
        print(f"  Listing already exists: {listing['address']}. Updating instead.")
        existing.update(listing)
    else:
        listings.append(listing)

    save_listings(listings)
    git_deploy('add', listing['address'])

    if sender:
        send_confirmation(sender, f"Listing Added: {listing['address']}",
                          f"Your listing at {listing['address']} has been added to whitakerexclusives.com.\n\nPrice: ${listing.get('price', 'N/A'):,}\nPhotos: {len(listing.get('photos', []))}\nStatus: Active")
    print(f"  Added: {listing['address']}")
    return True

def process_update(msg_data, listings):
    """Handle an Update Listing email."""
    body = msg_data.get('body', '')
    sender = ''
    headers = msg_data.get('headers', {})
    if isinstance(headers, dict):
        sender = headers.get('From', headers.get('from', ''))

    identifier = extract_identifier(body)
    if not identifier:
        print("  Error: No identifier found in Update Listing email")
        return False

    listing = find_listing(listings, identifier)
    if not listing:
        print(f"  Error: Listing not found: {identifier}")
        if sender:
            send_confirmation(sender, "Update Failed", f"Could not find listing matching: {identifier}")
        return False

    updates = parse_listing_from_body(body)
    updates = {k: v for k, v in updates.items() if v is not None and v != ''}
    updates.pop('id', None)

    listing.update(updates)
    save_listings(listings)
    git_deploy('update', listing['address'])

    if sender:
        send_confirmation(sender, f"Listing Updated: {listing['address']}",
                          f"Your listing at {listing['address']} has been updated.\n\nUpdated fields: {', '.join(updates.keys())}")
    print(f"  Updated: {listing['address']}")
    return True

def process_delete(msg_data, listings):
    """Handle a Delete Listing email."""
    body = msg_data.get('body', '')
    sender = ''
    headers = msg_data.get('headers', {})
    if isinstance(headers, dict):
        sender = headers.get('From', headers.get('from', ''))

    identifier = extract_identifier(body)
    if not identifier:
        print("  Error: No identifier found in Delete Listing email")
        return False

    listing = find_listing(listings, identifier)
    if not listing:
        print(f"  Error: Listing not found: {identifier}")
        if sender:
            send_confirmation(sender, "Delete Failed", f"Could not find listing matching: {identifier}")
        return False

    address = listing['address']
    listing_id = listing['id']
    listings.remove(listing)

    photo_dir = PHOTOS_DIR / listing_id
    if photo_dir.exists():
        shutil.rmtree(photo_dir)

    save_listings(listings)
    git_deploy('delete', address)

    if sender:
        send_confirmation(sender, f"Listing Deleted: {address}",
                          f"The listing at {address} has been removed from whitakerexclusives.com.")
    print(f"  Deleted: {address}")
    return True

def main():
    print(f"[{datetime.now().isoformat()}] Checking inbox...")

    ensure_processed_label()
    emails = get_emails()

    if not emails:
        print("  No new emails to process.")
        return

    listings = load_listings()
    processed_count = 0

    for email_item in emails:
        # Could be thread or message format
        thread_id = email_item.get('threadId', email_item.get('id', ''))
        msg_id = email_item.get('id', '')

        # If this is a thread, get the first message
        if 'messages' in email_item:
            msg_id = email_item['messages'][0].get('id', msg_id)

        subject = email_item.get('subject', email_item.get('snippet', '')).strip().lower()

        # Try to get subject from the search result
        if not any(cmd in subject for cmd in ['add listing', 'update listing', 'delete listing']):
            # Fetch the message to get subject
            msg_data = get_message(msg_id)
            if msg_data:
                headers = msg_data.get('headers', {})
                if isinstance(headers, dict):
                    subject = headers.get('Subject', headers.get('subject', '')).lower()
            if not any(cmd in subject for cmd in ['add listing', 'update listing', 'delete listing']):
                continue

        msg_data = get_message(msg_id)
        if not msg_data:
            print(f"  Could not read message {msg_id}")
            continue

        print(f"  Processing: {subject}")

        success = False
        if 'add listing' in subject:
            success = process_add(msg_data, listings)
        elif 'update listing' in subject:
            success = process_update(msg_data, listings)
        elif 'delete listing' in subject:
            success = process_delete(msg_data, listings)

        if success:
            processed_count += 1

        # Always label as processed
        label_processed(thread_id if thread_id else msg_id)

    print(f"  Done. Processed {processed_count} listing email(s).")

if __name__ == '__main__':
    main()
