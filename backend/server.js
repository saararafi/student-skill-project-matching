const express = require("express");

const app = express();

app.use(express.json());

const studentRoutes = require("./routes/studentRoutes");
const skillRoutes = require("./routes/skillroutes");
const projectRoutes = require("./routes/projectroutes");
const matchingRoutes = require("./routes/matchingroutes");
const errorHandler = require("./middleware/errorHandler");

app.use("/student", studentRoutes);
app.use("/skill", skillRoutes);
app.use("/project", projectRoutes);
app.use("/match", matchingRoutes);
app.use(errorHandler);

app.get("/", (req, res) => {
    res.send("Student Skill Project Backend is running!");
});

app.listen(5000, () => {
    console.log("Server running on http://localhost:5000");
});