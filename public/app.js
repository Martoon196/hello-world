const form = document.getElementById("form");
const drop = document.getElementById("drop");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const msg = document.getElementById("msg");
const submitBtn = document.getElementById("submit");
let files = [];

fetch("api/config").then((r) => r.json()).then((c) => {
  document.getElementById("accepted").textContent = `(${c.accepted})`;
}).catch(() => {});
document.getElementById("token").value = new URLSearchParams(location.search).get("token") || "";

function render() {
  fileList.innerHTML = "";
  files.forEach((f, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span>${f.name} <span class="muted">(${(f.size / 1024).toFixed(0)} KB)</span></span>`;
    const b = document.createElement("button");
    b.type = "button"; b.textContent = "Remove";
    b.onclick = () => { files.splice(i, 1); render(); };
    li.appendChild(b);
    fileList.appendChild(li);
  });
}
function addFiles(list) {
  for (const f of list) if (files.length < 8) files.push(f);
  render();
}
drop.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => { addFiles(fileInput.files); fileInput.value = ""; });
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
document.addEventListener("paste", (e) => {
  const items = [...(e.clipboardData?.files || [])];
  if (items.length) addFiles(items);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  msg.innerHTML = "";
  const fd = new FormData(form);
  fd.delete("files");
  files.forEach((f) => fd.append("files", f, f.name));
  if (!fd.get("notes").trim() && files.length === 0) {
    msg.innerHTML = `<div class="notice err">Paste the deal details or attach a file.</div>`;
    return;
  }
  submitBtn.disabled = true; submitBtn.textContent = "Sending...";
  try {
    const r = await fetch("api/deals", { method: "POST", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `Upload failed (${r.status})`);
    form.reset(); files = []; render();
    msg.innerHTML = `<div class="notice ok">Thanks, we've got it. We'll review the deal and come back to you.</div>`;
  } catch (err) {
    msg.innerHTML = `<div class="notice err">${err.message}</div>`;
  } finally {
    submitBtn.disabled = false; submitBtn.textContent = "Send deal";
  }
});
