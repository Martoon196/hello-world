<?php
// The Paddock signup -> Notion "Paddock Signups" database. Deploy in public_html/.
// Secrets live in apex-config.php ONE LEVEL ABOVE public_html — never in here.
//
// Expects apex-config.php to define:
//   NOTION_TOKEN           ntn_... / secret_...  (internal integration token)
//   NOTION_DATABASE_ID     Paddock Signups database id
//   PADDOCK_SHARED_SECRET  same value as PADDOCK_SHARED_SECRET in the members server's .env
//                          (optional: without it, signups stay Notion-only)
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

// The members server keeps the list, sends the welcome + guide + Sunday log, and
// handles unsubscribes. If it can't be reached, fall back to a welcome from here.
$forwarded = forward_to_members($email);

if ($status >= 200 && $status < 300) {
    if (!$forwarded) { send_welcome_email($email); }
    header('Location: /thanks.html'); exit;
}
if ($forwarded) { header('Location: /thanks.html'); exit; }
header('Location: /?signup=error#paddock');

function forward_to_members(string $email): bool
{
    if (!defined('PADDOCK_SHARED_SECRET') || PADDOCK_SHARED_SECRET === '') { return false; }
    $url = defined('MEMBERS_URL') ? MEMBERS_URL : 'https://members.apexcode.uk';
    $ch = curl_init(rtrim($url, '/') . '/public/paddock');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query(['email' => $email, 'source' => 'website']),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_HTTPHEADER     => ['X-Apex-Key: ' . PADDOCK_SHARED_SECRET],
    ]);
    $body = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    return $code === 200 && is_string($body) && strpos($body, '"ok":true') !== false;
}

// Welcome email via SiteGround's local mail for this domain (no SMTP creds needed).
// Failure is non-fatal: the signup is already captured in Notion.
function send_welcome_email(string $email): void
{
    $subject = "You're in — welcome to The Paddock";
    $body = <<<TXT
You're in.

The Paddock is the free tier of The Apex Code. Here's what lands in your inbox:

- The Bank Builder guide: https://apexcode.uk/bank-builder.html
- One free selection a week, with the full reasoning members get.
- The full results log every Sunday. Every bet, wins and losses alike.

The live feed runs on Telegram: https://t.me/TheApexCodeUK

Questions? Just reply to this email.

— The Apex Code
https://apexcode.uk

18+ only. Gamble responsibly: https://www.begambleaware.org
You joined this list at apexcode.uk. To leave it, reply with "unsubscribe".
TXT;
    $headers = "From: The Apex Code <hello@apexcode.uk>\r\n"
             . "Reply-To: hello@apexcode.uk\r\n"
             . "MIME-Version: 1.0\r\n"
             . "Content-Type: text/plain; charset=UTF-8\r\n";
    @mail($email, $subject, $body, $headers, '-fhello@apexcode.uk');
}
