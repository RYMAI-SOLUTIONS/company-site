document.addEventListener("DOMContentLoaded", function () {
    if (!window.THREE || !window.VANTA || !window.VANTA.BIRDS) {
        console.error("Vanta.BIRDS failed to initialize: THREE or VANTA.BIRDS not found.");
        return;
    }

    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches
    const backgroundColor = isDarkMode ? 0x0d0d0d : 0xffffff;

    // const heroContainer = document.querySelector('.hero');
    // const introContainer = document.querySelector('.intro');
    // if (introContainer && heroContainer) {
    //     introContainer.style.marginTop =  (heroContainer.offsetHeight + 40) + 'px';
    // }

    window.VANTA.BIRDS({
        el: ".hero",
        THREE: window.THREE,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        minHeight: 200.00,
        minWidth: 200.00,
        scale: 1.0,
        scaleMobile: 1.0,
        // backgroundColor: backgroundColor,
        backgroundColor: 0x000000,
        //backgroundColor: 0x000000,
        color1: 0xc18464,
        color2: 0x274394,
        colorMode: "lerp",
        birdSize: 0.30,
        speedLimit: 1.00,
        separation: 53.00,
        alignment: 91.00,
        cohesion: 0.3
    });
});
