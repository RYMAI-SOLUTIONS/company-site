const mobileMenu = document.querySelector('.mobile-menu');
if (mobileMenu) {
    mobileMenu.addEventListener('change', (event) => {
        const url = event.target.value;
        if (url) {
            window.location.replace(url);
        }
    });
}

const copyButtons = document.querySelectorAll('[data-copy-link]');
copyButtons.forEach((button) => {
    button.addEventListener('click', async () => {
        const link = button.getAttribute('data-copy-link');
        const original = button.textContent;
        const promptLabel = button.getAttribute('data-copy-prompt') || 'Copy this link:';

        const showCopied = () => {
            button.textContent = button.getAttribute('data-copied-label') || 'Copied';
            window.setTimeout(() => {
                button.textContent = original;
            }, 2000);
        };

        if (navigator.clipboard && window.isSecureContext) {
            try {
                await navigator.clipboard.writeText(link);
                showCopied();
            } catch (error) {
                window.prompt(promptLabel, link);
            }
        } else {
            window.prompt(promptLabel, link);
        }
    });
});
