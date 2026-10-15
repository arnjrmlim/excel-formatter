<?php
/**
 * IMS IT Ticketing System — Authentication Endpoint
 *
 * POST /api/auth.php?action=login    { username, password }
 * POST /api/auth.php?action=logout
 * GET  /api/auth.php?action=check
 */
declare(strict_types=1);

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/database.php';

sendApiHeaders();

$action = $_GET['action'] ?? '';

switch ($action) {

    // ── Login ─────────────────────────────────────────────────────────────────
    case 'login':
        requireMethod('POST');

        $body     = getJsonBody();
        $username = clean($body['username'] ?? '');
        $password = (string) ($body['password'] ?? '');

        if ($username === '' || $password === '') {
            jsonError('Username and password are required.', 422);
        }

        $user = Database::fetchOne(
            'SELECT * FROM `admin_users` WHERE `username` = ? AND `is_active` = 1 LIMIT 1',
            [$username]
        );

        if ($user === null) {
            // Constant-time compare to avoid timing attacks
            password_verify('dummy', '$2y$12$invalidsaltinvalidsaltinvalidsaltinva');
            jsonError('Invalid credentials.', 401);
        }

        // Support both old JS SHA-256 hashes (migration path) and modern bcrypt
        $valid = false;
        if (str_starts_with($user['password_hash'], '$2y$')) {
            // Modern bcrypt row
            $valid = password_verify($password, $user['password_hash']);
        } else {
            // Legacy JS hash: sha256(salt:password) — kept for migration
            $legacyHash = hash('sha256', $user['password_salt'] . ':' . $password);
            $valid       = hash_equals($user['password_hash'], $legacyHash);

            // Opportunistically upgrade to bcrypt
            if ($valid) {
                $newHash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
                Database::execute(
                    'UPDATE `admin_users` SET `password_hash` = ?, `password_salt` = \'\'
                     WHERE `id` = ?',
                    [$newHash, $user['id']]
                );
            }
        }

        if (!$valid) {
            jsonError('Invalid credentials.', 401);
        }

        // Start session
        getAdminSessionUser(); // boots session
        session_regenerate_id(true);

        $_SESSION['admin_user'] = [
            'id'       => (int) $user['id'],
            'username' => $user['username'],
            'name'     => $user['name'],
            'role'     => $user['role'],
        ];

        jsonSuccess([
            'username'    => $user['username'],
            'name'        => $user['name'],
            'role'        => $user['role'],
        ], 'Login successful.');

    // ── Logout ────────────────────────────────────────────────────────────────
    case 'logout':
        requireMethod('POST');

        if (session_status() === PHP_SESSION_NONE) {
            session_name(SESSION_NAME);
            session_start();
        }
        $_SESSION = [];
        session_destroy();

        jsonSuccess(null, 'Logged out.');

    // ── Check session ─────────────────────────────────────────────────────────
    case 'check':
        requireMethod('GET');

        $user = getAdminSessionUser();
        if ($user === null) {
            jsonError('Not authenticated.', 401);
        }
        jsonSuccess($user, 'Authenticated.');

    default:
        jsonError('Unknown action.', 404);
}
