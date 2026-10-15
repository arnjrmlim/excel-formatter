<?php
/**
 * IMS IT Ticketing System — Central Configuration
 * Edit this file before first deployment.
 */
declare(strict_types=1);

// ── Database ─────────────────────────────────────────────────────────────────
define('DB_HOST',    'localhost');
define('DB_PORT',    '3306');
define('DB_NAME',    'ims_tickets');
define('DB_USER',    'root');   // XAMPP default
define('DB_PASS',    '');       // XAMPP default — empty password
define('DB_CHARSET', 'utf8mb4');

// ── Application ───────────────────────────────────────────────────────────────
// Base URL of the portal (no trailing slash).
define('APP_BASE_URL', 'http://ims-portal');
define('APP_TIMEZONE', 'Asia/Manila');

// ── File uploads ─────────────────────────────────────────────────────────────
// Absolute path to the uploads directory on disk.
define('UPLOAD_DIR',      dirname(__DIR__) . DIRECTORY_SEPARATOR . 'uploads');
// URL path for serving uploaded files (relative to APP_BASE_URL).
define('UPLOAD_URL_PATH', '/uploads');
// Maximum upload size in bytes (5 MB default).
define('UPLOAD_MAX_BYTES', 5 * 1024 * 1024);
// Allowed MIME types for screenshots.
define('UPLOAD_ALLOWED_MIME', ['image/jpeg', 'image/png', 'image/gif', 'image/webp']);

// ── Session ───────────────────────────────────────────────────────────────────
define('SESSION_NAME',     'ims_admin_session');
define('SESSION_LIFETIME', 28800); // 8 hours in seconds

// ── Security ─────────────────────────────────────────────────────────────────
// Set to true when serving over HTTPS (strongly recommended in production).
define('SECURE_COOKIE', false);

// ── Pagination ────────────────────────────────────────────────────────────────
define('DEFAULT_PAGE_SIZE', 25);
define('MAX_PAGE_SIZE',    200);

// ── Environment ───────────────────────────────────────────────────────────────
// 'production' suppresses error details in API responses.
// 'development' returns full error messages (use only on dev machines).
// TODO: switch back to 'production' before going live.
define('APP_ENV', 'development');

// ── Bootstrap ────────────────────────────────────────────────────────────────
date_default_timezone_set(APP_TIMEZONE);

if (APP_ENV === 'development') {
    ini_set('display_errors', '1');
    error_reporting(E_ALL);
} else {
    ini_set('display_errors', '0');
    error_reporting(0);
}

/**
 * Send CORS + JSON content-type headers for every API response.
 * Call this at the top of every endpoint file.
 */
function sendApiHeaders(): void
{
    // LAN-only deployment — restrict to same origin.
    // Add your portal origin here if the API is on a different port.
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate');
    header('X-Content-Type-Options: nosniff');

    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(204);
        exit;
    }
}

/**
 * Return a standardised success JSON response and exit.
 *
 * @param mixed  $data    Payload to include under the "data" key.
 * @param string $message Human-readable message.
 * @param int    $code    HTTP status code.
 */
function jsonSuccess(mixed $data = null, string $message = 'OK', int $code = 200): never
{
    http_response_code($code);
    $body = ['success' => true, 'message' => $message];
    if ($data !== null) {
        $body['data'] = $data;
    }
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/**
 * Return a standardised error JSON response and exit.
 */
function jsonError(string $message, int $code = 400): never
{
    http_response_code($code);
    $detail = (APP_ENV === 'development') ? ['trace' => debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 3)] : null;
    $body   = ['success' => false, 'message' => $message];
    if ($detail) {
        $body['debug'] = $detail;
    }
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/**
 * Require a specific HTTP method; send 405 otherwise.
 */
function requireMethod(string ...$methods): void
{
    if (!in_array($_SERVER['REQUEST_METHOD'], $methods, true)) {
        jsonError('Method Not Allowed', 405);
    }
}

/**
 * Require an active admin session; send 401 otherwise.
 * Returns the session user array on success.
 */
function requireAdminSession(): array
{
    $user = getAdminSessionUser();
    if ($user === null) {
        jsonError('Unauthorised — admin login required', 401);
    }
    return $user;
}

/**
 * Return the current admin session user, or null if not authenticated.
 */
function getAdminSessionUser(): ?array
{
    if (session_status() === PHP_SESSION_NONE) {
        session_name(SESSION_NAME);
        session_set_cookie_params([
            'lifetime' => SESSION_LIFETIME,
            'path'     => '/',
            'secure'   => SECURE_COOKIE,
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }

    if (!empty($_SESSION['admin_user']) && is_array($_SESSION['admin_user'])) {
        return $_SESSION['admin_user'];
    }
    return null;
}

/**
 * Read and decode the raw JSON request body.
 * Returns an empty array if the body is absent or malformed.
 */
function getJsonBody(): array
{
    $raw = file_get_contents('php://input');
    if (!$raw) {
        return [];
    }
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : [];
}

/**
 * Sanitise a plain-text string: trim + strip tags + limit length.
 */
function clean(mixed $value, int $maxLength = 500): string
{
    return mb_substr(strip_tags(trim((string) ($value ?? ''))), 0, $maxLength);
}
