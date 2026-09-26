const express = require("express");

const router = express.Router();

// Temporary student data
let students = [
    {
        id: 1,
        name: "Madiha",
        skills: ["Python", "Java", "React"]
    }
];

// Temporary project data
let projects = [
    {
        id: 1,
        title: "College Bus Tracking System",
        requiredSkills: ["Python", "React"]
    },
    {
        id: 2,
        title: "Student Management System",
        requiredSkills: ["Java", "SQL"]
    }
];

// Find projects matching a student's skills
router.get("/:studentId", (req, res) => {

    const student = students.find(
        s => s.id == req.params.studentId
    );

    if (!student) {
        return res.status(404).json({
            message: "Student not found"
        });
    }

    const matchingProjects = projects.filter(project => {

        return project.requiredSkills.some(skill =>
            student.skills.includes(skill)
        );

    });

    res.json({
        student: student.name,
        skills: student.skills,
        matchingProjects: matchingProjects
    });
});

module.exports = router;