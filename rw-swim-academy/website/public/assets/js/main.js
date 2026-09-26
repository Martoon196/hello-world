// RW Swim Academy — shared behaviour
(function () {
  const toggle = document.querySelector(".nav-toggle");
  if (toggle) toggle.addEventListener("click", () => {
    const open = document.body.classList.toggle("nav-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  const y = document.getElementById("year"); if (y) y.textContent = new Date().getFullYear();

  // Netlify forms: show a friendly confirmation without leaving the page when JS is on.
  document.querySelectorAll("form[data-netlify]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      if (form.dataset.native === "true") return; // let it post normally
      e.preventDefault();
      const btn = form.querySelector("button[type=submit]");
      const status = form.querySelector(".form-status") || form.appendChild(Object.assign(document.createElement("div"), { className: "form-status" }));
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Sending…';
      try {
        const body = new URLSearchParams(new FormData(form)).toString();
        const res = await fetch("/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
        if (!res.ok) throw new Error("bad status " + res.status);
        status.className = "form-status alert alert--ok";
        status.textContent = form.dataset.success || "Thanks! We've got your message and will reply within one working day.";
        form.reset();
      } catch (err) {
        status.className = "form-status alert alert--warn";
        status.innerHTML = 'Sorry, that didn\'t send. Email us at <a href="mailto:hello@rwswimacademy.co.uk">hello@rwswimacademy.co.uk</a>.';
      } finally { btn.disabled = false; btn.textContent = btn.dataset.label || "Send"; }
    });
  });
})();
