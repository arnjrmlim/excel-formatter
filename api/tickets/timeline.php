<?php
/**
 * IMS IT Ticketing System — GET /api/tickets/timeline.php?id=<id>
 * Returns all timeline log entries for a ticket, ordered oldest-first.
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('GET');

$id = (int) ($_GET['id'] ?? 0);
if ($id <= 0) {
    jsonError('A valid ticket id is required.', 422);
}

$exists = Database::fetchOne('SELECT `id` FROM `tickets` WHERE `id` = ?', [$id]);
if ($exists === null) {
    jsonError('Ticket not found.', 404);
}

$logs = Database::fetchAll(
    'SELECT * FROM `ticket_logs` WHERE `ticket_id` = ? ORDER BY `created_at` ASC',
    [$id]
);

jsonSuccess(array_map('logToApi', $logs));
