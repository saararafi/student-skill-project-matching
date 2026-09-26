const express = require("express");

const router = express.Router();

let skills = [];

// Get all skills
router.get("/", (req, res) => {
    res.json(skills);
});

// Get skill by ID
router.get("/:id", (req, res) => {
    const skill = skills.find(s => s.id == req.params.id);

    if (!skill) {
        return res.status(404).json({
            message: "Skill not found"
        });
    }

    res.json(skill);
});

// Add a skill
router.post("/", (req, res) => {
    const skill = {
        id: skills.length + 1,
        name: req.body.name
    };

    skills.push(skill);

    res.status(201).json({
        message: "Skill added successfully",
        skill: skill
    });
});

module.exports = router;