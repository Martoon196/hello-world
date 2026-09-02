<?php
// The Paddock signup -> Brevo (double opt-in). Deploy in public_html/.
// Secrets live in apex-config.php ONE LEVEL ABOVE public_html — never in here.
//
// Expects apex-config.php to define:
//   BREVO_API_KEY          xkeysib-...
//   BREVO_LIST_ID          (int) "The Paddock" list id
//   BREVO_DOI_TEMPLATE_ID  (int) double-opt-in confirmation template id
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
    'email'          => $email,
    'includeListIds' => [ (int)BREVO_LIST_ID ],
    'templateId'     => (int)BREVO_DOI_TEMPLATE_ID,
    'redirectionUrl' => 'https://apexcode.uk/thanks.html',
]);

$ch = curl_init('https://api.brevo.com/v3/contacts/doubleOptinConfirmation');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $payload,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 15,
    CURLOPT_HTTPHEADER     => [
        'accept: application/json',
        'content-type: application/json',
        'api-key: ' . BREVO_API_KEY,
    ],
]);
curl_exec($ch);
$status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);

// 2xx = queued; 400 with "already exists" also fine for the visitor's purposes.
if ($status >= 200 && $status < 500) { header('Location: /thanks.html'); exit; }
header('Location: /?signup=error#paddock');
