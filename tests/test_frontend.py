"""
Frontend regression tests.

These guard the stylesheet against the class of bug where a page uses a
class name that has no rule in style.css, which silently leaves those
elements unstyled.
"""

import glob
import io
import os
import re
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND = os.path.join(BASE_DIR, 'frontend')
CSS_DIR = os.path.join(FRONTEND, 'css')
STYLESHEET = os.path.join(CSS_DIR, 'style.css')
DESIGN_SYSTEM = os.path.join(CSS_DIR, 'design-system.css')

# Classes that are created at runtime by JavaScript rather than present in
# the static HTML, so they cannot be discovered by scanning the markup.
RUNTIME_ONLY_CLASSES = {
    'visible', 'is-visible', 'active', 'show', 'applied', 'read', 'unread',
    'withdrawn', 'status-withdrawn', 'application-withdrawn',
}


def read(path):
    with io.open(path, encoding='utf-8', newline='') as f:
        return f.read().replace('\r\n', '\n')


def stylesheets():
    """Every stylesheet the pages can load."""
    return [STYLESHEET, DESIGN_SYSTEM]


def classes_used_in_html():
    used = {}
    for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
        raw = read(path)
        for match in re.finditer(r'class="([^"]*)"', raw):
            for name in match.group(1).split():
                used.setdefault(name, set()).add(os.path.basename(path))
    return used


def classes_defined_in_css():
    defined = set()
    for sheet in stylesheets():
        raw = read(sheet).lower()
        defined |= set(re.findall(r'\.([a-z_][\w-]*)', raw))
    return defined


class TestStylesheetCoverage(unittest.TestCase):
    """Every class used in the markup must have a rule in style.css."""

    def test_every_used_class_has_a_css_rule(self):
        defined = classes_defined_in_css()
        used = classes_used_in_html()

        missing = {
            name: sorted(files)
            for name, files in used.items()
            if name.lower() not in defined
            and name not in RUNTIME_ONLY_CLASSES
        }

        self.assertEqual(
            missing, {},
            "These classes are used in the HTML but have no rule in "
            f"style.css: {missing}"
        )

    def test_stylesheet_is_not_empty(self):
        self.assertGreater(len(read(STYLESHEET)), 20000)

    def test_design_system_is_linked_from_every_app_page(self):
        """The landing and sign-in pages keep their own standalone styling."""
        standalone = {'index.html', 'login.html'}
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            name = os.path.basename(path)
            if name in standalone:
                continue
            raw = read(path)
            with self.subTest(page=name):
                self.assertIn('css/design-system.css', raw)

    def test_accessibility_basics(self):
        """The design system must provide visible focus and reduced motion."""
        css = read(DESIGN_SYSTEM)
        self.assertIn(':focus-visible', css)
        self.assertIn('prefers-reduced-motion', css)


class TestOriginalThemePreserved(unittest.TestCase):
    """
    Guards the original olive-and-gold botanical identity.

    The design system is allowed to add to the theme, but it must not
    redefine the parts that carry it.
    """

    @classmethod
    def setUpClass(cls):
        cls.css = read(STYLESHEET)

    def test_sidebar_is_the_deep_olive_panel(self):
        """The signature dark olive navigation rail must stay dark."""
        self.assertRegex(
            self.css,
            r'\.sidebar\s*\{[^}]*background:\s*var\(--olive-deep\)',
            'the sidebar must keep its deep-olive background'
        )

    def test_sidebar_caption_stays_light_gold(self):
        """Cream gold reads correctly on the dark olive panel."""
        self.assertRegex(
            self.css,
            r'\.sidebar-caption\s*\{[^}]*color:\s*var\(--gold-light\)'
        )

    def test_buttons_keep_the_gold_border(self):
        """The gold-outlined button is the original call to action."""
        self.assertRegex(
            self.css,
            r'\.garden-button\s*\{[^}]*border:\s*1px solid var\(--gold'
        )
        self.assertRegex(
            self.css,
            r'\.garden-button:hover\s*\{[^}]*background:\s*var\(--olive-deep'
        )

    def test_score_ring_keeps_its_gold_halo(self):
        """The soft gold halo around the score ring is part of the look."""
        self.assertIn(
            '0 0 0 7px rgba(198, 161, 91, 0.06)',
            self.css
        )

    def test_skill_plant_grows_from_a_stem(self):
        """The plant rises from an olive base line, not a boxed card."""
        self.assertRegex(
            self.css,
            r'\.skill-plant\s*\{[^}]*border-bottom:\s*2px solid var\(--olive'
        )
        self.assertRegex(
            self.css,
            r'\.skill-plant\s*\{[^}]*linear-gradient\(\s*to top'
        )

    def test_skill_flower_is_gold_and_sways(self):
        self.assertRegex(
            self.css,
            r'\.skill-plant-flower\s*\{[^}]*color:\s*var\(--gold'
        )
        self.assertIn('gentleSway', self.css)

    def test_progress_bars_run_olive_to_gold(self):
        self.assertRegex(
            self.css,
            r'\.match-component-fill\s*\{[^}]*var\(--olive[^}]*var\(--gold'
        )

    def test_selected_chip_uses_a_soft_olive_tint(self):
        self.assertRegex(
            self.css,
            r'\.settings-chip\.selected span\s*\{[^}]*rgba\(110, 125, 70'
        )

    def test_design_system_does_not_override_the_theme(self):
        """
        The design system may add transitions and states, but it must not
        change the properties that carry the olive-and-gold identity.
        """
        ds = read(DESIGN_SYSTEM)

        forbidden = [
            # selector, property that would change the theme
            (r'\.sidebar\s*\{', 'background'),
            (r'\.sidebar-caption\s*\{', 'color'),
            (r'\.garden-button\s*\{', 'border-radius'),
            (r'\.garden-button\s*\{', 'background'),
            (r'\.match-score-circle\s*\{', 'background'),
            (r'\.match-score-circle\s*\{', 'box-shadow'),
            (r'\.capacity-ring\s*\{', 'background'),
            (r'\.skill-plant\s*\{', 'background'),
            (r'\.skill-plant\s*\{', 'border-bottom'),
            (r'\.settings-chip\.selected[^{]*\{', 'background'),
            (r'\.match-component-fill\s*\{', 'background'),
        ]

        for selector, prop in forbidden:
            for match in re.finditer(selector + r'[^{}]*\{([^}]*)\}', ds):
                body = match.group(1)
                if re.search(r'(?<![\w-])' + re.escape(prop) + r'\s*:', body):
                    self.fail(
                        f'the design system must not set "{prop}" on '
                        f'{selector.strip(chr(92)+"s")} - it would change the '
                        'original olive-and-gold theme'
                    )

    def test_pages_load_the_shared_stylesheet(self):
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            raw = read(path)
            with self.subTest(page=os.path.basename(path)):
                self.assertIn('css/style.css', raw)

    def test_pages_load_the_shared_script(self):
        """Every interactive page needs main.js for its API wiring."""
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            name = os.path.basename(path)
            if name == 'index.html':
                continue
            raw = read(path)
            with self.subTest(page=name):
                self.assertIn('js/main.js', raw)

    def test_pages_load_the_live_data_layer(self):
        """live.js turns the pages into database-driven views."""
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            raw = read(path)
            with self.subTest(page=os.path.basename(path)):
                self.assertIn('js/live.js', raw)

    def test_pages_use_the_shared_app_shell(self):
        """All app pages should share one sidebar/layout structure."""
        for name in ['dashboard.html', 'growth.html', 'profile.html', 'projects.html',
                     'project-details.html', 'team.html', 'gaps.html',
                     'applications.html', 'notifications.html',
                     'settings.html', 'faculty.html', 'faculty-applications.html',
                     'faculty-certificates.html', 'faculty-projects.html',
                     'faculty-new-project.html']:
            raw = read(os.path.join(FRONTEND, name))
            with self.subTest(page=name):
                self.assertIn('app-body', raw)
                self.assertIn('app-layout', raw)
                self.assertIn('class="sidebar"', raw)
                self.assertIn('app-main', raw)

    def test_html_tags_are_balanced(self):
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            raw = read(path)
            name = os.path.basename(path)
            with self.subTest(page=name):
                for tag in ['div', 'section', 'main', 'aside', 'header',
                            'footer', 'form', 'article', 'nav']:
                    opened = len(re.findall(r'<' + tag + r'[\s>]', raw))
                    closed = len(re.findall(r'</' + tag + r'>', raw))
                    self.assertEqual(
                        opened, closed,
                        f'{name}: <{tag}> opened {opened} times but closed {closed} times'
                    )

    def test_no_duplicate_element_ids(self):
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            raw = read(path)
            name = os.path.basename(path)
            ids = re.findall(r'\sid="([^"]+)"', raw)
            duplicates = {i for i in ids if ids.count(i) > 1}
            with self.subTest(page=name):
                self.assertEqual(duplicates, set(), f'{name}: duplicate ids {duplicates}')

    def test_no_literal_unicode_escapes_leaked_into_html(self):
        """A stray '\\u2767' in the markup would render as broken text."""
        for path in sorted(glob.glob(os.path.join(FRONTEND, '*.html'))):
            raw = read(path)
            name = os.path.basename(path)
            with self.subTest(page=name):
                self.assertNotIn(
                    '\\u', raw,
                    f'{name}: contains a literal \\u escape sequence'
                )


if __name__ == '__main__':
    unittest.main(verbosity=2)
