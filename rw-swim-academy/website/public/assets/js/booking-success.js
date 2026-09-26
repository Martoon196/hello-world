// Optional: personalise the success page with the Stripe session id (for support queries).
(function () {
  const id = new URLSearchParams(location.search).get("session_id");
  if (id) { const p = document.getElementById("success-copy"); if (p) p.insertAdjacentHTML("afterend", `<p class="small muted">Booking reference: ${id.slice(-8).toUpperCase()}</p>`); }
})();
