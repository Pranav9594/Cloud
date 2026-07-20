document.addEventListener("DOMContentLoaded", () => {
    let pendingDeleteForm = null;

    const modal = document.getElementById("pin-modal");
    const pinInput = document.getElementById("pin-input");
    const pinError = document.getElementById("pin-error");

    document.querySelectorAll("[data-confirm-delete='true']").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            pendingDeleteForm = form;
            pinInput.value = "";
            pinError.style.display = "none";
            pinError.classList.add("hidden");
            modal.style.display = "flex";
            modal.classList.remove("hidden");
            setTimeout(() => pinInput.focus(), 50);
        });
    });

    document.getElementById("pin-confirm").addEventListener("click", () => {
        if (pinInput.value.trim() === "6") {
            modal.style.display = "none";
            modal.classList.add("hidden");
            if (pendingDeleteForm) {
                pendingDeleteForm.submit();
            }
        } else {
            pinError.style.display = "block";
            pinError.classList.remove("hidden");
            pinInput.value = "";
            pinInput.focus();
        }
    });

    document.getElementById("pin-cancel").addEventListener("click", () => {
        modal.style.display = "none";
        modal.classList.add("hidden");
        pendingDeleteForm = null;
    });

    document.querySelectorAll(".flash").forEach((flashMessage) => {
        window.setTimeout(() => {
            flashMessage.style.transition = "opacity 0.35s ease, transform 0.35s ease";
            flashMessage.style.opacity = "0";
            flashMessage.style.transform = "translateY(-4px)";
        }, 3800);
    });
});
