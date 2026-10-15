<?php
/**
 * IMS IT Ticketing System — GET /api/tickets/get.php?id=<id>
 * Returns a single ticket with its full timeline logs.
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

$ticket = Database::fetchOne('SELECT * FROM `tickets` WHERE `id` = ?', [$id]);
if ($ticket === null) {
    jsonError('Ticket not found.', 404);
}

// Fetch timeline ordered oldest-first (matches existing UI expectation)
$logs = Database::fetchAll(
    'SELECT * FROM `ticket_logs` WHERE `ticket_id` = ? ORDER BY `created_at` ASC',
    [$id]
);

$isAdmin = getAdminSessionUser() !== null;

$data = ticketToApi($ticket);
if (!$isAdmin) {
    unset($data['adminNotes'], $data['launchParams']);
}
$data['logs'] = array_map('logToApi', $logs);

jsonSuccess($data);
