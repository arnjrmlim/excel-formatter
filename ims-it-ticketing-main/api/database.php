<?php
/**
 * IMS IT Ticketing System — PDO Database Layer
 */
declare(strict_types=1);

require_once __DIR__ . '/config.php';

class Database
{
    private static ?PDO $instance = null;

    public static function get(): PDO
    {
        if (self::$instance === null) {
            $dsn = sprintf(
                'mysql:host=%s;port=%s;dbname=%s;charset=%s',
                DB_HOST, DB_PORT, DB_NAME, DB_CHARSET
            );
            try {
                self::$instance = new PDO($dsn, DB_USER, DB_PASS, [
                    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::ATTR_EMULATE_PREPARES   => false,
                    PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
                ]);
            } catch (PDOException $e) {
                $msg = APP_ENV === 'development'
                    ? 'Database connection failed: ' . $e->getMessage()
                    : 'Database connection failed.';
                jsonError($msg, 503);
            }
        }
        return self::$instance;
    }

    /**
     * Execute a SELECT and return all rows.
     */
    public static function fetchAll(string $sql, array $params = []): array
    {
        $stmt = self::get()->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }

    /**
     * Execute a SELECT and return one row, or null.
     */
    public static function fetchOne(string $sql, array $params = []): ?array
    {
        $stmt = self::get()->prepare($sql);
        $stmt->execute($params);
        $row = $stmt->fetch();
        return $row !== false ? $row : null;
    }

    /**
     * Execute INSERT/UPDATE/DELETE; return affected rows.
     */
    public static function execute(string $sql, array $params = []): int
    {
        $stmt = self::get()->prepare($sql);
        $stmt->execute($params);
        return $stmt->rowCount();
    }

    /**
     * Execute INSERT and return the new auto-increment ID.
     */
    public static function insert(string $sql, array $params = []): int
    {
        self::execute($sql, $params);
        return (int) self::get()->lastInsertId();
    }
}

/**
 * Generate the next ticket number for a given year using an atomic counter.
 * Uses SELECT … FOR UPDATE inside a transaction to prevent duplicates under
 * concurrent inserts.
 *
 * @return string  e.g. "IT-2026-000001"
 */
function generateTicketNumber(int $year): string
{
    $db = Database::get();
    $db->beginTransaction();
    try {
        // Lock the row for this year
        $row = $db->query(
            "SELECT `seq` FROM `ticket_number_seq` WHERE `year` = $year FOR UPDATE"
        )->fetch(PDO::FETCH_ASSOC);

        if ($row === false) {
            // First ticket of this year
            $db->exec("INSERT INTO `ticket_number_seq` (`year`, `seq`) VALUES ($year, 1)");
            $seq = 1;
        } else {
            $seq = (int)$row['seq'] + 1;
            $db->exec("UPDATE `ticket_number_seq` SET `seq` = $seq WHERE `year` = $year");
        }

        $db->commit();
        return sprintf('IT-%d-%06d', $year, $seq);
    } catch (Throwable $e) {
        $db->rollBack();
        throw $e;
    }
}

/**
 * Insert a timeline log entry for a ticket.
 */
function insertTicketLog(
    int    $ticketId,
    string $action,
    string $admin   = 'System',
    string $notes   = '',
    string $oldStatus = '',
    string $newStatus = ''
): int {
    return Database::insert(
        'INSERT INTO `ticket_logs`
            (`ticket_id`, `action`, `old_status`, `new_status`, `admin`, `notes`)
         VALUES (?, ?, ?, ?, ?, ?)',
        [
            $ticketId,
            $action,
            $oldStatus ?: null,
            $newStatus ?: null,
            $admin,
            $notes ?: null,
        ]
    );
}

/**
 * Map a database ticket row to the JSON shape the frontend expects.
 * Keeps camelCase field names consistent with the old localStorage format.
 */
function ticketToApi(array $row): array
{
    return [
        'id'                  => (string) $row['id'],
        'ticketNumber'        => $row['ticket_number'],
        'employeeName'        => $row['employee_name'],
        'department'          => $row['department'],
        'contact'             => $row['email'],
        'computerName'        => $row['computer_name'],
        'category'            => $row['category'],
        'priority'            => $row['priority'],
        'description'         => $row['description'],
        'screenshotPath'      => $row['screenshot_path'] ?? '',
        'screenshotUrl'       => $row['screenshot_path']
            ? APP_BASE_URL . UPLOAD_URL_PATH . '/' . basename($row['screenshot_path'])
            : '',
        'status'              => $row['status'],
        'assignedTechnician'  => $row['assigned_technician'] ?? '',
        'adminNotes'          => $row['admin_notes'] ?? '',
        'launchParams'        => isset($row['launch_params'])
            ? json_decode($row['launch_params'], true)
            : null,
        'createdDate'         => $row['created_at'],
        'updatedDate'         => $row['updated_at'],
        'resolvedDate'        => $row['resolved_at'] ?? '',
    ];
}

/**
 * Map a database log row to the JSON shape the frontend expects.
 */
function logToApi(array $row): array
{
    return [
        'id'        => (int) $row['id'],
        'action'    => $row['action'],
        'oldStatus' => $row['old_status'] ?? '',
        'newStatus' => $row['new_status'] ?? '',
        'admin'     => $row['admin'],
        'notes'     => $row['notes'] ?? '',
        'dateTime'  => $row['created_at'],
    ];
}
