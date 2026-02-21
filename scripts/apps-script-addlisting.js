/**
 * Google Apps Script — Whitaker Exclusives Add Listing Webhook v2
 * 
 * Photos upload to Google Drive, email contains links only.
 * No more attachment size limits.
 * 
 * SETUP:
 * 1. Go to script.google.com → New Project
 * 2. Paste this entire file
 * 3. Deploy → New Deployment → Web App
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Copy the Web App URL
 * 5. Update WEBHOOK_URL in addlisting.html
 * 
 * On first run, it will ask for Drive + Gmail permissions — approve them.
 */

// Root folder name in Google Drive
var DRIVE_FOLDER_NAME = 'Whitaker Exclusives Listings';

function getOrCreateFolder(parentFolder, name) {
  var folders = parentFolder.getFoldersByName(name);
  if (folders.hasNext()) return folders.next();
  return parentFolder.createFolder(name);
}

function getRootFolder() {
  var folders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  if (folders.hasNext()) return folders.next();
  return DriveApp.createFolder(DRIVE_FOLDER_NAME);
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    // Check if this is a photo upload chunk or the final submission
    if (data.action === 'upload_photo') {
      return handlePhotoUpload(data);
    }
    
    if (data.action === 'submit_listing') {
      return handleSubmitListing(data);
    }
    
    // Legacy: single-request mode (no photos or small payload)
    return handleLegacySubmit(data);
    
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'error', message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

function handlePhotoUpload(data) {
  var rootFolder = getRootFolder();
  var listingFolder = getOrCreateFolder(rootFolder, data.folderId);
  
  var blob = Utilities.newBlob(
    Utilities.base64Decode(data.photoData),
    data.mimeType || 'image/jpeg',
    data.fileName || 'photo.jpg'
  );
  
  var file = listingFolder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  
  var fileId = file.getId();
  var directUrl = 'https://lh3.googleusercontent.com/d/' + fileId;
  
  return ContentService.createTextOutput(
    JSON.stringify({ 
      status: 'ok', 
      fileId: fileId,
      url: directUrl,
      name: file.getName()
    })
  ).setMimeType(ContentService.MimeType.JSON);
}

function handleSubmitListing(data) {
  // Build email body
  var body = '';
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
  
  // Add photo URLs
  if (data.photoUrls && data.photoUrls.length > 0) {
    body += '\nPhotos:\n';
    for (var i = 0; i < data.photoUrls.length; i++) {
      body += data.photoUrls[i] + '\n';
    }
  }
  
  // Add Drive folder link
  if (data.folderId) {
    var rootFolder = getRootFolder();
    var folders = rootFolder.getFoldersByName(data.folderId);
    if (folders.hasNext()) {
      var folder = folders.next();
      body += '\nPhoto Folder: ' + folder.getUrl() + '\n';
    }
  }
  
  MailApp.sendEmail({
    to: 'chad@whitakerexclusives.com',
    subject: 'Add Listing',
    body: body,
  });
  
  MailApp.sendEmail({
    to: 'chad@whitakerexclusives.com',
    subject: 'New Listing Submitted: ' + (data.address || 'Unknown'),
    body: 'A new listing was submitted via the website form.\n\n' + body + '\n\nPhotos: ' + ((data.photoUrls && data.photoUrls.length) || 0) + '\n\nThis will be automatically processed within 15 minutes.',
  });
  
  return ContentService.createTextOutput(
    JSON.stringify({ status: 'ok', message: 'Listing submitted' })
  ).setMimeType(ContentService.MimeType.JSON);
}

function handleLegacySubmit(data) {
  // Fallback for requests without action field
  data.action = 'submit_listing';
  data.photoUrls = [];
  return handleSubmitListing(data);
}

function doGet(e) {
  return ContentService.createTextOutput(
    JSON.stringify({ status: 'ok', message: 'Whitaker Exclusives Add Listing Webhook v2' })
  ).setMimeType(ContentService.MimeType.JSON);
}
