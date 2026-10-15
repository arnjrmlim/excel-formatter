<?php
/**
 * IMS IT Ticketing System — DELETE /api/tickets/delete.php?id=<id>
 * Admin only. Cancels (soft-delete) or permanently deletes a ticket.
 *
 * Query params:
 *   id    int   ticket ID
 *   hard  1     set to permanently delete (default: soft cancel)
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('DELETE', 'POST');

$admin = requireAdminSession();

$id   = (int) ($_GET['id']   ?? 0);
$hard = (int) ($_GET['hard'] ?? 0);

if ($id <= 0) {
    jsonError('A valid ticket id is required.', 422);
}

$ticket = Database::fetchOne('SELECT `id`, `ticket_number`, `status` FROM `tickets` WHERE `id` = ?', [$id]);
if ($ticket === null) {
    jsonError('Ticket not found.', 404);
}

$adminName = ($admin['name'] ?? $admin['username']);

if ($hard === 1) {
    // Permanent delete — cascade removes logs and attachments via FK
    // Delete physical attachment files first
    $attachments = Database::fetchAll(
        'SELECT `path` FROM `ticket_attachments` WHERE `ticket_id` = ?',
        [$id]
    );
    foreach ($attachments as $att) {
        $filePath = UPLOAD_DIR . DIRECTORY_SEPARATOR . basename($att['path']);
        if (is_file($filePath)) {
            @unlink($filePath);
        }
    }

    Database::execute('DELETE FROM `tickets` WHERE `id` = ?', [$id]);
    jsonSuccess(null, "Ticket {$ticket['ticket_number']} permanently deleted.");
} else {
    // Soft delete: set status to Cancelled + log it
    Database::execute(
        'UPDATE `tickets` SET `status` = \'Cancelled\', `updated_at` = NOW() WHERE `id` = ?',
        [$id]
    );
    insertTicketLog(
        $id,
        'Status Changed',
        $adminName,
        "Ticket cancelled by {$adminName}.",
        $ticket['status'],
        'Cancelled'
    );
    jsonSuccess(['id' => $id, 'status' => 'Cancelled'], "Ticket {$ticket['ticket_number']} cancelled.");
}
