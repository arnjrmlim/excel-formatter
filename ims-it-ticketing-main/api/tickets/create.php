<?php
/**
 * IMS IT Ticketing System — POST /api/tickets/create.php
 * Create a new ticket. No authentication required (employee-facing).
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('POST');

$body = getJsonBody();

// ── Validation ────────────────────────────────────────────────────────────────
$allowed_categories = ['Hardware','Software','Network','Printer','Email','Account','Other'];
$allowed_priorities  = ['Low','Normal','High','Critical'];

$employeeName = clean($body['employeeName'] ?? '');
$department   = clean($body['department']   ?? '');
$contact      = clean($body['contact']      ?? '');
$computerName = clean($body['computerName'] ?? 'Unknown Device', 120);
$category     = clean($body['category']     ?? '');
$priority     = clean($body['priority']     ?? 'Normal');
$description  = clean($body['description']  ?? '', 5000);
$launchParams = isset($body['launchParams']) && is_array($body['launchParams'])
    ? json_encode($body['launchParams'], JSON_UNESCAPED_UNICODE)
    : null;

if ($employeeName === '') jsonError('Employee name is required.',  422);
if ($department   === '') jsonError('Department is required.',     422);
if ($description  === '') jsonError('Description is required.',    422);
if (!in_array($category, $allowed_categories, true)) jsonError('Invalid category.',  422);
if (!in_array($priority,  $allowed_priorities,  true)) jsonError('Invalid priority.', 422);

// Validate computer name: letters, digits, hyphens, max 253 chars
if ($computerName !== 'Unknown Device' && !preg_match('/^[A-Za-z0-9\-]{1,253}$/', $computerName)) {
    $computerName = 'Unknown Device';
}

// ── Generate ticket number (atomic) ──────────────────────────────────────────
$year = (int) date('Y');
try {
    $ticketNumber = generateTicketNumber($year);
} catch (Throwable $e) {
    jsonError('Failed to generate ticket number. Please try again.', 500);
}

// ── Insert ticket ─────────────────────────────────────────────────────────────
$now = date('Y-m-d H:i:s');

try {
    $ticketId = Database::insert(
        'INSERT INTO `tickets`
            (`ticket_number`, `employee_name`, `department`, `email`,
             `computer_name`, `category`, `priority`, `description`,
             `launch_params`, `status`, `created_at`, `updated_at`)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, \'Pending\', ?, ?)',
        [
            $ticketNumber, $employeeName, $department, $contact,
            $computerName, $category, $priority, $description,
            $launchParams, $now, $now,
        ]
    );

    // Initial timeline entry
    insertTicketLog(
        $ticketId,
        'Ticket Created',
        'Employee',
        "Ticket submitted from employee request form. Workstation: {$computerName}.",
        '',
        'Pending'
    );
} catch (Throwable $e) {
    $msg = APP_ENV === 'development' ? $e->getMessage() : 'Failed to create ticket.';
    jsonError($msg, 500);
}

// ── Return created ticket ────────────────────────────────────────────────────
$ticket = Database::fetchOne('SELECT * FROM `tickets` WHERE `id` = ?', [$ticketId]);

jsonSuccess(ticketToApi($ticket), 'Ticket created.', 201);
