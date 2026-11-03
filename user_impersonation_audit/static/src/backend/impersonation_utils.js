export function formatRemaining(seconds) {
    const s = Math.max(0, Math.floor(seconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const pad = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${pad(m)}:${pad(s % 60)}` : `${pad(m)}:${pad(s % 60)}`;
}

// Returning switches accounts: always a POST with the CSRF token, never a plain link.
export function postReturn() {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "/impersonation/return";
    const token = document.createElement("input");
    token.type = "hidden";
    token.name = "csrf_token";
    token.value = odoo.csrf_token;
    form.append(token);
    document.body.append(form);
    form.submit();
}
