const express = require("express");

const router = express.Router();

let projects = [];

// Get all projects
router.get("/", (req, res) => {
    res.json(projects);
});

// Get project by ID
router.get("/:id", (req, res) => {
    const project = projects.find(p => p.id == req.params.id);

    if (!project) {
        return res.status(404).json({
            message: "Project not found"
        });
    }

    res.json(project);
});

// Add a project
router.post("/", (req, res) => {
    const project = {
        id: projects.length + 1,
        title: req.body.title,
        description: req.body.description,
        requiredSkills: req.body.requiredSkills || []
    };

    projects.push(project);

    res.status(201).json({
        message: "Project added successfully",
        project: project
    });
});

module.exports = router;