/**
 * Google Apps Script — Whitaker Exclusives Add Listing Webhook
 * 
 * SETUP:
 * 1. Go to script.google.com → New Project
 * 2. Paste this entire file
 * 3. Deploy → New Deployment → Web App
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Copy the Web App URL
 * 5. Replace %%APPS_SCRIPT_URL%% in addlisting.html with the URL
 */

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    // Build email body in the format the inbox parser expects
    let body = '';
    body += 'Address: ' + (data.address || '') + '\n';
    body += 'City: ' + (data.city || 'Fort Lauderdale') + '\n';
    body += 'State: ' + (data.state || 'FL') + '\n';
    body += 'Zip: ' + (data.zip || '') + '\n';
    body += 'Price: ' + (data.price || '') + '\n';
    body += 'Beds: ' + (data.beds || '') + '\n';
    body += 'Baths: ' + (data.baths || '') + '\n';
    body += 'Sqft: ' + (data.sqft || '') + '\n';
    body += 'Year Built: ' + (data.yearBuilt || '') + '\n';
    body += 'Lot Size: ' + (data.lotSize || '') + '\n';
    body += 'MLS: ' + (data.mls || '') + '\n';
    body += 'Agent: ' + (data.agent || 'Chad Whitaker') + '\n';
    body += 'Description: ' + (data.description || '') + '\n';
    body += 'Features: ' + (data.features || '') + '\n';
    
    // Handle photo attachments
    var attachments = [];
    if (data.photos && data.photos.length > 0) {
      for (var i = 0; i < data.photos.length; i++) {
        var photo = data.photos[i];
        var blob = Utilities.newBlob(
          Utilities.base64Decode(photo.data),
          photo.type || 'image/jpeg',
          photo.name || ('photo-' + (i + 1) + '.jpg')
        );
        attachments.push(blob);
      }
    }
    
    // Send email to chad@whitakerexclusives.com with "Add Listing" subject
    var emailOptions = {
      to: 'chad@whitakerexclusives.com',
      subject: 'Add Listing',
      body: body,
    };
    
    if (attachments.length > 0) {
      emailOptions.attachments = attachments;
    }
    
    MailApp.sendEmail(emailOptions);
    
    // Also send notification to admin
    MailApp.sendEmail({
      to: 'chad@whitakerexclusives.com',
      subject: 'New Listing Submitted: ' + (data.address || 'Unknown'),
      body: 'A new listing was submitted via the website form.\n\n' + body + '\n\nPhotos attached: ' + (attachments.length) + '\n\nThis will be automatically processed within 15 minutes.',
    });
    
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'ok', message: 'Listing submitted' })
    ).setMimeType(ContentService.MimeType.JSON);
    
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'error', message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(
    JSON.stringify({ status: 'ok', message: 'Whitaker Exclusives Add Listing Webhook' })
  ).setMimeType(ContentService.MimeType.JSON);
}
