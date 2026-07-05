const pathSegments = window.location.pathname.split('/').filter(Boolean);

let currentLang = 'en';
if (pathSegments.length > 0 && /^[a-z]{2}$/.test(pathSegments[0])) {
    currentLang = pathSegments[0];
}

const mobileMenu = document.querySelector('.mobile-menu');
if (mobileMenu) {
    mobileMenu.value = currentLang;

    mobileMenu.addEventListener('change', (event) => {
        event.preventDefault();
        let location = window.location.pathname;
        let replaced = location.replace(/^\/[a-z]{2}\//, '/' + event.target.value + '/');
        window.location.replace(replaced);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    AOS.init();
});
