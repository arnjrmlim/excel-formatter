<?php
/**
 * IMS IT Ticketing System — GET /api/tickets/list.php
 *
 * Query parameters:
 *   page      int    (default 1)
 *   limit     int    (default 25, max 200)
 *   search    string full-text search across key fields
 *   status    string exact status filter
 *   priority  string exact priority filter
 *   category  string exact category filter
 *   sort      string column key (ticketNumber|employeeName|department|
 *                                computerName|category|priority|status|createdDate)
 *   dir       string asc|desc (default desc for date, asc for others)
 *   dateFrom  string YYYY-MM-DD
 *   dateTo    string YYYY-MM-DD
 *
 * No authentication required (read-only list used by employee view too).
 * Admin-only fields (adminNotes) are stripped for unauthenticated callers.
 */
declare(strict_types=1);

require_once dirname(__DIR__) . '/config.php';
require_once dirname(__DIR__) . '/database.php';

sendApiHeaders();
requireMethod('GET');

// ── Pagination ────────────────────────────────────────────────────────────────
$page  = max(1, (int) ($_GET['page']  ?? 1));
$limit = min(MAX_PAGE_SIZE, max(1, (int) ($_GET['limit'] ?? DEFAULT_PAGE_SIZE)));
$offset = ($page - 1) * $limit;

// ── Filters ───────────────────────────────────────────────────────────────────
$search   = clean($_GET['search']   ?? '', 200);
$status   = clean($_GET['status']   ?? '');
$priority = clean($_GET['priority'] ?? '');
$category = clean($_GET['category'] ?? '');
$dateFrom = clean($_GET['dateFrom'] ?? '');
$dateTo   = clean($_GET['dateTo']   ?? '');

$validStatuses    = ['Pending','In Progress','Waiting for User','Resolved','Closed','Cancelled'];
$validPriorities  = ['Low','Normal','High','Critical'];
$validCategories  = ['Hardware','Software','Network','Printer','Email','Account','Other'];

if ($status   !== '' && !in_array($status,   $validStatuses,   true)) $status   = '';
if ($priority !== '' && !in_array($priority, $validPriorities, true)) $priority = '';
if ($category !== '' && !in_array($category, $validCategories, true)) $category = '';

// ── Sorting ───────────────────────────────────────────────────────────────────
$sortMap = [
    'ticketNumber' => 'ticket_number',
    'employeeName' => 'employee_name',
    'department'   => 'department',
    'computerName' => 'computer_name',
    'category'     => 'category',
    'priority'     => 'priority',
    'status'       => 'status',
    'createdDate'  => 'created_at',
];
$sortKey = $_GET['sort'] ?? 'createdDate';
$sortCol = $sortMap[$sortKey] ?? 'created_at';
$sortDir = strtolower($_GET['dir'] ?? '') === 'asc' ? 'ASC' : 'DESC';

// ── Build WHERE clause ────────────────────────────────────────────────────────
$where  = [];
$params = [];

if ($search !== '') {
    // Use LIKE for broader compatibility; FULLTEXT index used by MySQL optimizer
    // when the table is large enough.
    $like = '%' . $search . '%';
    $where[]  = '(`ticket_number` LIKE ? OR `employee_name` LIKE ? OR `department` LIKE ?
                   OR `computer_name` LIKE ? OR `category` LIKE ? OR `description` LIKE ?)';
    $params = array_merge($params, [$like, $like, $like, $like, $like, $like]);
}

if ($status   !== '') { $where[] = '`status` = ?';   $params[] = $status;   }
if ($priority !== '') { $where[] = '`priority` = ?'; $params[] = $priority; }
if ($category !== '') { $where[] = '`category` = ?'; $params[] = $category; }

if ($dateFrom !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $dateFrom)) {
    $where[]  = '`created_at` >= ?';
    $params[] = $dateFrom . ' 00:00:00';
}
if ($dateTo !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $dateTo)) {
    $where[]  = '`created_at` <= ?';
    $params[] = $dateTo . ' 23:59:59';
}

$whereSQL = $where ? 'WHERE ' . implode(' AND ', $where) : '';

// ── Count ────────────────────────────────────────────────────────────────────
$total = (int) Database::fetchOne(
    "SELECT COUNT(*) AS cnt FROM `tickets` $whereSQL",
    $params
)['cnt'];

// ── Fetch page ────────────────────────────────────────────────────────────────
$rows = Database::fetchAll(
    "SELECT * FROM `tickets` $whereSQL ORDER BY `$sortCol` $sortDir LIMIT ? OFFSET ?",
    array_merge($params, [$limit, $offset])
);

// Is the caller an admin? Strip sensitive fields for unauthenticated callers.
$isAdmin = getAdminSessionUser() !== null;

$tickets = array_map(function (array $row) use ($isAdmin): array {
    $t = ticketToApi($row);
    if (!$isAdmin) {
        unset($t['adminNotes'], $t['launchParams']);
    }
    return $t;
}, $rows);

jsonSuccess([
    'tickets'    => $tickets,
    'total'      => $total,
    'page'       => $page,
    'limit'      => $limit,
    'totalPages' => (int) ceil($total / $limit),
]);
