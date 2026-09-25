/* =========================================================
   SKILLMATCH FRONTEND
   Temporary frontend interactions
   Backend integration will come later.
   ========================================================= */


document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {

        loginForm.addEventListener("submit", function (event) {

            event.preventDefault();

            const email =
                document.getElementById("email").value;

            const password =
                document.getElementById("password").value;


            if (!email || !password) {

                alert("Please fill in both fields.");

                return;
            }


            /*
             * TEMPORARY:
             * This will later send the information
             * to Flask for real authentication.
             */

            window.location.href = "dashboard.html";

        });

    }


    /* Simple scroll animation */

    const revealElements =
        document.querySelectorAll(
            ".feature-card, .growth-item, .journey-card"
        );


    const observer =
        new IntersectionObserver(
            function (entries) {

                entries.forEach(function (entry) {

                    if (entry.isIntersecting) {

                        entry.target.style.opacity = "1";

                        entry.target.style.transform =
                            "translateY(0)";

                    }

                });

            },
            {
                threshold: 0.15
            }
        );


    revealElements.forEach(function (element) {

        element.style.opacity = "0";

        element.style.transform =
            "translateY(20px)";

        element.style.transition =
            "opacity .7s ease, transform .7s ease";

        observer.observe(element);

    });

});