<?php
// The Paddock signup -> Notion "Paddock Signups" database. Deploy in public_html/.
// Secrets live in apex-config.php ONE LEVEL ABOVE public_html — never in here.
//
// Expects apex-config.php to define:
//   NOTION_TOKEN        ntn_... / secret_...  (internal integration token)
//   NOTION_DATABASE_ID  Paddock Signups database id
declare(strict_types=1);

$config = dirname(__DIR__) . '/apex-config.php';
if (!is_readable($config)) { http_response_code(500); exit('Configuration missing.'); }
require $config;

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { header('Location: /'); exit; }

// Honeypot: humans never see the "company" field; bots fill it. Pretend success.
if (!empty($_POST['company'])) { header('Location: /thanks.html'); exit; }

$email = trim((string)($_POST['email'] ?? ''));
if ($email === '' || strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    header('Location: /?signup=invalid#paddock'); exit;
}

$payload = json_encode([
    'parent' => ['database_id' => NOTION_DATABASE_ID],
    'properties' => [
        'Email'  => ['title' => [['text' => ['content' => $email]]]],
        'Source' => ['select' => ['name' => 'website']],
        'Status' => ['select' => ['name' => 'new']],
    ],
]);

$ch = curl_init('https://api.notion.com/v1/pages');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $payload,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 15,
    CURLOPT_HTTPHEADER     => [
        'Authorization: Bearer ' . NOTION_TOKEN,
        'Notion-Version: 2022-06-28',
        'Content-Type: application/json',
    ],
]);
curl_exec($ch);
$status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);

if ($status >= 200 && $status < 300) { header('Location: /thanks.html'); exit; }
header('Location: /?signup=error#paddock');
