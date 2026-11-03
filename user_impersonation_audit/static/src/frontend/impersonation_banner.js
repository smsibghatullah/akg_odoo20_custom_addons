// Countdown of the server-rendered impersonation banner on portal / website pages.
import { formatRemaining, postReturn } from "@user_impersonation_audit/backend/impersonation_utils";

function start() {
    const banner = document.querySelector(".o_uia_banner_frontend");
    if (!banner) {
        return;
    }
    document.body.classList.add("o_uia_active");
    const deadline = Date.now() + parseInt(banner.dataset.remaining || "0") * 1000;
    const counter = banner.querySelector(".o_uia_countdown");
    const tick = () => {
        const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
        counter.textContent = formatRemaining(left);
        banner.classList.toggle("o_uia_warning", left < 300);
        if (left === 0) {
            clearInterval(timer);
            postReturn();
        }
    };
    const timer = setInterval(tick, 1000);
    tick();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
} else {
    start();
}
