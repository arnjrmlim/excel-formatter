<?php
/**
 * IMS IT Ticketing System — GET /api/dashboard/stats.php
 * Returns ticket counts for the admin dashboard cards.
 * Admin session required.
 *
 * Uses separate queries for MariaDB 10.4 compatibility — the combined
 * multi-expression CASE WHEN prepared statement fails to parse on MariaDB 10.4.
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('GET');
requireAdminSession();

$today     = date('Y-m-d');
$monthFrom = date('Y-m-01');
$weekFrom  = date('Y-m-d', strtotime('monday this week'));

// ── Status counts ─────────────────────────────────────────────────────────────
$counts = Database::fetchOne(
    "SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
        SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
        SUM(CASE WHEN status = 'Waiting for User' THEN 1 ELSE 0 END) AS waiting,
        SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved,
        SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) AS closed,
        SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
        SUM(CASE WHEN status NOT IN ('Resolved','Closed','Cancelled') THEN 1 ELSE 0 END) AS open
    FROM `tickets`",
    []
);

// ── Priority counts ───────────────────────────────────────────────────────────
$highPriority = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets` WHERE priority IN ('High','Critical')"
)['cnt'];

$openCritical = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets`
     WHERE priority = 'Critical' AND status NOT IN ('Resolved','Closed','Cancelled')"
)['cnt'];

// ── Date-range counts ─────────────────────────────────────────────────────────
$todayCount = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets` WHERE DATE(created_at) = ?",
    [$today]
)['cnt'];

$weekCount = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets` WHERE DATE(created_at) >= ?",
    [$weekFrom]
)['cnt'];

$monthCount = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets` WHERE DATE(created_at) >= ?",
    [$monthFrom]
)['cnt'];

// ── Top categories ────────────────────────────────────────────────────────────
$topCategories = Database::fetchAll(
    "SELECT `category`, COUNT(*) AS cnt FROM `tickets` GROUP BY `category` ORDER BY cnt DESC LIMIT 5"
);

// ── Top departments ───────────────────────────────────────────────────────────
$topDepartments = Database::fetchAll(
    "SELECT `department`, COUNT(*) AS cnt FROM `tickets` GROUP BY `department` ORDER BY cnt DESC LIMIT 5"
);

// ── Average resolution time (hours) ──────────────────────────────────────────
$avgRow = Database::fetchOne(
    "SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, resolved_at)) AS avg_hours FROM `tickets` WHERE resolved_at IS NOT NULL"
);

jsonSuccess([
    'total'              => (int) $counts['total'],
    'pending'            => (int) $counts['pending'],
    'inProgress'         => (int) $counts['in_progress'],
    'waiting'            => (int) $counts['waiting'],
    'resolved'           => (int) $counts['resolved'],
    'closed'             => (int) $counts['closed'],
    'cancelled'          => (int) $counts['cancelled'],
    'open'               => (int) $counts['open'],
    'highPriority'       => $highPriority,
    'openCritical'       => $openCritical,
    'today'              => $todayCount,
    'thisWeek'           => $weekCount,
    'thisMonth'          => $monthCount,
    'avgResolutionHours' => $avgRow['avg_hours'] !== null
        ? round((float) $avgRow['avg_hours'], 1)
        : null,
    'topCategories'      => $topCategories,
    'topDepartments'     => $topDepartments,
]);
