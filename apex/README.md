# Apex Code site wiring (apexcode.uk on SiteGround)

No secrets in this directory, ever. Keys arrive via environment variables at
run time; the live Brevo key lives only in `apex-config.php` ABOVE public_html.

## Order of operations

1. `STRIPE_KEY=rk_live_... bash apex/provision_stripe.sh`
   → products, monthly+annual prices, 3 payment links (prints JOIN_* URLs)
2. `BREVO_KEY=xkeysib-... bash apex/provision_brevo.sh`
   → "The Paddock" list + DOI template (prints the two IDs)
3. Fill `site/apex-config.example.php` → `apex-config.php` with the Brevo key + IDs
4. Edit `deploy/index.html`: JOIN_* → payment links, PADDOCK_FORM → `/subscribe.php`
   (method POST, email field name "email", hidden `company` honeypot), plus
   TELEGRAM_LINK and CONTACT_EMAIL
5. Upload: `index.html`, `subscribe.php`, `thanks.html` → public_html;
   `apex-config.php` → one level above public_html
6. Test: form submit with a real inbox (expect DOI email → thanks.html), open
   each JOIN link and check the price before closing the tab

## SiteGround paths

public_html: `/home/customer/www/apexcode.uk/public_html`
config:      `/home/customer/www/apexcode.uk/apex-config.php`

## Also wire (betbot server, config/settings.yaml)

Paste the five `price_...` ids printed by provision_stripe.sh into
`apex.stripe_prices` so Stripe purchases map to membership tiers.
