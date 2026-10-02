/* =========================================
   STUDENT SKILL & PROJECT MATCHING SYSTEM
   JAVASCRIPT
   ========================================= */


/* ---------- LOGIN ---------- */

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", function(event) {

        event.preventDefault();

        const email =
            document.getElementById("email").value;

        const password =
            document.getElementById("password").value;

        const role =
            document.getElementById("role").value;


        if (email === "" || password === "") {

            alert("Please fill all the fields.");

            return;
        }


        /*
           This is temporary frontend logic.

           Later your Flask backend will
           authenticate the user.
        */

        if (role === "student") {

            window.location.href =
                "dashboard.html";

        } else {

            alert(
                "Faculty dashboard will be connected with the backend."
            );

        }

    });

}


/* ---------- REGISTRATION ---------- */

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        function(event) {

            event.preventDefault();


            const name =
                document.getElementById("name").value;

            const email =
                document.getElementById("registerEmail").value;

            const department =
                document.getElementById("department").value;

            const year =
                document.getElementById("year").value;

            const password =
                document.getElementById("registerPassword").value;


            if (
                name === "" ||
                email === "" ||
                department === "" ||
                year === "" ||
                password === ""
            ) {

                alert(
                    "Please fill all the fields."
                );

                return;
            }


            alert(
                "Registration successful!"
            );


            window.location.href =
                "login.html";

        }
    );

}