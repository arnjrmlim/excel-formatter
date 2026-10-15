<?php
/**
 * IMS IT Ticketing System — PATCH /api/tickets/update.php?id=<id>
 * Admin only. Updates status, technician, and/or admin notes.
 * Auto-generates timeline entries for each changed field.
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('POST', 'PATCH', 'PUT');  // accept POST for broad IIS/PHP compat

$admin = requireAdminSession();

$id = (int) ($_GET['id'] ?? 0);
if ($id <= 0) {
    jsonError('A valid ticket id is required.', 422);
}

$ticket = Database::fetchOne('SELECT * FROM `tickets` WHERE `id` = ?', [$id]);
if ($ticket === null) {
    jsonError('Ticket not found.', 404);
}

$body = getJsonBody();

$validStatuses = ['Pending','In Progress','Waiting for User','Resolved','Closed','Cancelled'];

$newStatus     = clean($body['status']              ?? $ticket['status']);
$newTechnician = clean($body['assignedTechnician']  ?? ($ticket['assigned_technician'] ?? ''), 160);
$newNotes      = clean($body['adminNotes']          ?? ($ticket['admin_notes'] ?? ''), 5000);

if (!in_array($newStatus, $validStatuses, true)) {
    jsonError('Invalid status value.', 422);
}

$adminName = $admin['name'] ?? $admin['username'];
$now       = date('Y-m-d H:i:s');
$setClauses = ['`updated_at` = ?'];
$setParams  = [$now];
$logEntries = [];

// Detect technician change
$oldTechnician = $ticket['assigned_technician'] ?? '';
if ($newTechnician !== $oldTechnician) {
    $setClauses[] = '`assigned_technician` = ?';
    $setParams[]  = $newTechnician ?: null;
    $logEntries[] = [
        'action'    => 'Assigned',
        'notes'     => $newTechnician
            ? "Assigned to {$newTechnician}."
            : 'Technician cleared.',
        'oldStatus' => $ticket['status'],
        'newStatus' => $ticket['status'],
    ];
}

// Detect status change
if ($newStatus !== $ticket['status']) {
    $setClauses[] = '`status` = ?';
    $setParams[]  = $newStatus;

    if ($newStatus === 'Resolved') {
        $setClauses[] = '`resolved_at` = ?';
        $setParams[]  = $now;
    }

    $logEntries[] = [
        'action'    => 'Status Changed',
        'notes'     => "Status changed from {$ticket['status']} to {$newStatus}.",
        'oldStatus' => $ticket['status'],
        'newStatus' => $newStatus,
    ];
}

// Detect notes change
$oldNotes = $ticket['admin_notes'] ?? '';
if ($newNotes !== $oldNotes) {
    $setClauses[] = '`admin_notes` = ?';
    $setParams[]  = $newNotes ?: null;
    $logEntries[] = [
        'action'    => 'Notes Added',
        'notes'     => $newNotes ?: 'Notes cleared.',
        'oldStatus' => $newStatus,
        'newStatus' => $newStatus,
    ];
}

// Only write if something actually changed
if (count($setClauses) > 1) {
    $setParams[] = $id;
    Database::execute(
        'UPDATE `tickets` SET ' . implode(', ', $setClauses) . ' WHERE `id` = ?',
        $setParams
    );

    foreach ($logEntries as $entry) {
        insertTicketLog(
            $id,
            $entry['action'],
            $adminName,
            $entry['notes'],
            $entry['oldStatus'],
            $entry['newStatus']
        );
    }
}

// Return updated ticket with logs
$updated = Database::fetchOne('SELECT * FROM `tickets` WHERE `id` = ?', [$id]);
$logs    = Database::fetchAll(
    'SELECT * FROM `ticket_logs` WHERE `ticket_id` = ? ORDER BY `created_at` ASC',
    [$id]
);

$data         = ticketToApi($updated);
$data['logs'] = array_map('logToApi', $logs);

jsonSuccess($data, 'Ticket updated.');
