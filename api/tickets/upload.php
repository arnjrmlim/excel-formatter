<?php
/**
 * IMS IT Ticketing System — POST /api/tickets/upload.php?ticket_id=<id>
 * Accepts a multipart screenshot upload, validates it, stores it in /uploads/,
 * records the path in the ticket row and attachment table, and logs the action.
 *
 * File field name: screenshot
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('POST');

$ticketId = (int) ($_GET['ticket_id'] ?? 0);
if ($ticketId <= 0) {
    jsonError('A valid ticket_id is required.', 422);
}

$ticket = Database::fetchOne('SELECT `id`, `ticket_number` FROM `tickets` WHERE `id` = ?', [$ticketId]);
if ($ticket === null) {
    jsonError('Ticket not found.', 404);
}

// ── File validation ───────────────────────────────────────────────────────────
if (!isset($_FILES['screenshot']) || $_FILES['screenshot']['error'] !== UPLOAD_ERR_OK) {
    $err = $_FILES['screenshot']['error'] ?? -1;
    $msg = match ((int) $err) {
        UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE => 'File exceeds maximum allowed size.',
        UPLOAD_ERR_PARTIAL   => 'File was only partially uploaded.',
        UPLOAD_ERR_NO_FILE   => 'No file was uploaded.',
        default              => 'Upload error code ' . $err,
    };
    jsonError($msg, 422);
}

$file     = $_FILES['screenshot'];
$tmpPath  = $file['tmp_name'];
$origName = basename($file['name']);
$size     = (int) $file['size'];

if ($size > UPLOAD_MAX_BYTES) {
    jsonError('File exceeds maximum size of ' . round(UPLOAD_MAX_BYTES / 1048576, 1) . ' MB.', 422);
}

// Validate actual MIME type from file content (not just Content-Type header)
$finfo    = new finfo(FILEINFO_MIME_TYPE);
$mimeType = $finfo->file($tmpPath);

if (!in_array($mimeType, UPLOAD_ALLOWED_MIME, true)) {
    jsonError('Only JPEG, PNG, GIF, and WebP images are allowed.', 422);
}

// ── Path traversal prevention ─────────────────────────────────────────────────
$ext      = match ($mimeType) {
    'image/jpeg' => 'jpg',
    'image/png'  => 'png',
    'image/gif'  => 'gif',
    'image/webp' => 'webp',
    default      => 'bin',
};
$stored   = sprintf('%s_%s.%s', date('Ymd_His'), bin2hex(random_bytes(8)), $ext);
$destPath = rtrim(UPLOAD_DIR, '/\\') . DIRECTORY_SEPARATOR . $stored;

// Ensure upload directory exists
if (!is_dir(UPLOAD_DIR)) {
    mkdir(UPLOAD_DIR, 0750, true);
}

if (!move_uploaded_file($tmpPath, $destPath)) {
    jsonError('Failed to store the uploaded file.', 500);
}

// ── Persist to database ───────────────────────────────────────────────────────
$relPath = $stored; // relative to UPLOAD_DIR

Database::execute(
    'UPDATE `tickets` SET `screenshot_path` = ?, `updated_at` = NOW() WHERE `id` = ?',
    [$relPath, $ticketId]
);

Database::insert(
    'INSERT INTO `ticket_attachments`
        (`ticket_id`, `filename`, `original`, `mime_type`, `size_bytes`, `path`, `uploaded_by`)
     VALUES (?, ?, ?, ?, ?, ?, ?)',
    [$ticketId, $stored, $origName, $mimeType, $size, $relPath, 'Employee']
);

insertTicketLog(
    $ticketId,
    'Attachment Uploaded',
    'Employee',
    "Screenshot uploaded: {$origName}."
);

$url = APP_BASE_URL . UPLOAD_URL_PATH . '/' . $stored;
jsonSuccess(['path' => $relPath, 'url' => $url], 'Screenshot uploaded.', 201);
