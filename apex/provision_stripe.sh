#!/usr/bin/env bash
# TASK 1 — Create Apex Code products, prices, and payment links (LIVE mode).
# Usage: STRIPE_KEY=rk_live_... bash apex/provision_stripe.sh
# Prints price IDs and the three payment link URLs. Never echoes the key.
set -euo pipefail
: "${STRIPE_KEY:?set STRIPE_KEY=rk_live_...}"

API="https://api.stripe.com/v1"
SUCCESS_URL="https://apexcode.uk/"

req() { curl -fsS -u "$STRIPE_KEY:" "$@"; }

jqget() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d$1)"; }

find_or_create_product() { # name -> product id
  local name="$1"
  local existing
  existing=$(req "$API/products?limit=100&active=true" \
    | python3 -c "import sys,json;print(next((p['id'] for p in json.load(sys.stdin)['data'] if p['name']==\"$name\"),''))")
  if [ -n "$existing" ]; then echo "$existing"; return; fi
  req -X POST "$API/products" -d "name=$name" | jqget "['id']"
}

create_price() { # product_id amount_pence interval -> price id
  req -X POST "$API/prices" \
    -d "product=$1" -d "unit_amount=$2" -d "currency=gbp" \
    -d "recurring[interval]=$3" | jqget "['id']"
}

create_link() { # price_id -> url
  req -X POST "$API/payment_links" \
    -d "line_items[0][price]=$1" -d "line_items[0][quantity]=1" \
    -d "after_completion[type]=redirect" \
    -d "after_completion[redirect][url]=$SUCCESS_URL" | jqget "['url']"
}

echo "== Products =="
P_FOUNDING=$(find_or_create_product "Apex Code — Founding 50")
P_MEMBER=$(find_or_create_product "Apex Code — Member")
P_PRO=$(find_or_create_product "Apex Code — Pro")
echo "founding=$P_FOUNDING member=$P_MEMBER pro=$P_PRO"

echo "== Prices =="
PRICE_FOUNDING_M=$(create_price "$P_FOUNDING" 1495 month)
PRICE_MEMBER_M=$(create_price "$P_MEMBER" 2495 month)
PRICE_MEMBER_Y=$(create_price "$P_MEMBER" 24900 year)
PRICE_PRO_M=$(create_price "$P_PRO" 4495 month)
PRICE_PRO_Y=$(create_price "$P_PRO" 44900 year)
printf "founding_monthly=%s\nmember_monthly=%s\nmember_yearly=%s\npro_monthly=%s\npro_yearly=%s\n" \
  "$PRICE_FOUNDING_M" "$PRICE_MEMBER_M" "$PRICE_MEMBER_Y" "$PRICE_PRO_M" "$PRICE_PRO_Y"

echo "== Payment links (monthly; annual prices exist for later) =="
echo "JOIN_FOUNDING=$(create_link "$PRICE_FOUNDING_M")"
echo "JOIN_MEMBER=$(create_link "$PRICE_MEMBER_M")"
echo "JOIN_PRO=$(create_link "$PRICE_PRO_M")"

echo
echo "Paste the five price_... ids into config/settings.yaml apex.stripe_prices like:"
echo "  $PRICE_FOUNDING_M: {tier: founding, period: monthly}"
