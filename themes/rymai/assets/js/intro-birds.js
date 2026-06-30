document.addEventListener("DOMContentLoaded", function () {
    AOS.init();

    if (!window.THREE || !window.VANTA || !window.VANTA.BIRDS) {
        console.error("Vanta.BIRDS failed to initialize: THREE or VANTA.BIRDS not found.");
        return;
    }

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
        backgroundColor: 0x0d0d0d,
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
