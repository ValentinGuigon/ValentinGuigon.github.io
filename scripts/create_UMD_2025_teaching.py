#!/usr/bin/env python3
"""
Generate merged-topic teaching pages for UMD 2025.

Creates:
- _teaching/2025_UMD_course_syllabus.md
- _teaching/2025_UMD_course_<topic_slug>.md for each merged topic bundle

Assumptions (edit if needed):
- PDFs live at:  assets/pdf/UMD_2025/<slug>.pdf
- Thumbnails at: assets/img/UMD_2025/<slug>.png
- PDF.js viewer exists at: /assets/pdfjs/web/viewer.html

Run:
  python3 generate_teaching_umd_2025_merged.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re


# ----------------------------
# User-editable parameters
# ----------------------------

YEAR = 2025
# must match teaching.md display_categories if you filter by category
CATEGORY = "UMD 2025"
OUTPUT_DIR = Path("_teaching")

PDF_BASE = "/assets/pdf/UMD_2025"  # site-relative
IMG_BASE = "/assets/img/UMD_2025"  # site-relative

# Syllabus page (you decide the actual file names)
SYLLABUS_SLUG = "syllabus"
SYLLABUS_TITLE = "UMD 2025 NACS 645: Syllabus"
SYLLABUS_DESCRIPTION = "Course overview, policies, schedule, and reading list."
SYLLABUS_PDF = f"{PDF_BASE}/NACS_645_syllabus.pdf"
SYLLABUS_IMG = f"{IMG_BASE}/syllabus.png"

# Optional: warn if expected PDF/PNG files don't exist locally
CHECK_FILES_EXIST = True


# ----------------------------
# Data model
# ----------------------------

@dataclass(frozen=True)
class Bundle:
    slug: str
    title: str
    description: str
    importance: int
    # purely informational (e.g., ["Sep 9", "Sep 11"])
    sessions: List[str]
    # citations/reading list lines (you provide exact formatting)
    readings: List[str]


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def md_for_bundle(bundle: Bundle) -> str:
    pdf = f"{PDF_BASE}/{bundle.slug}.pdf"
    img = f"{IMG_BASE}/{bundle.slug}.png"

    sessions_line = ""
    if bundle.sessions:
        sessions_line = "Sessions covered: " + \
            ", ".join(bundle.sessions) + ".\n"

    readings_block = ""
    if bundle.readings:
        readings_block = "\nRequired readings:\n\n" + \
            "\n".join([f"- {r}" for r in bundle.readings]) + "\n"

    return f"""---
layout: page
title: {bundle.title}
description: {bundle.description}
img: {img}
importance: {bundle.importance}
category: "{CATEGORY}"
year: {YEAR}
pdf: {pdf}
---

Course material for **NACS 645: Introduction to Cognitive Science (Fall {YEAR})** at the University of Maryland.
{sessions_line}{readings_block}
The material is provided below as a single PDF.

<p>
  <a href="{{{{ page.pdf | relative_url }}}}" target="_blank" rel="noopener">
    Open or download the course PDF
  </a>
</p>

<div style="width:100%; height:900px;">
  <iframe
    src="{{{{ '/assets/pdfjs/web/viewer.html?file=' | relative_url }}}}{{{{ page.pdf | relative_url | uri_escape }}}}"
    width="100%"
    height="100%"
    style="border:0;"
  ></iframe>
</div>
"""


def md_for_syllabus() -> str:
    return f"""---
layout: page
title: {SYLLABUS_TITLE}
description: {SYLLABUS_DESCRIPTION}
img: {SYLLABUS_IMG}
importance: 0
category: "{CATEGORY}"
year: {YEAR}
pdf: {SYLLABUS_PDF}
---

Syllabus for **NACS 645: Introduction to Cognitive Science (Fall {YEAR})** at the University of Maryland.

<p>
  <a href="{{{{ page.pdf | relative_url }}}}" target="_blank" rel="noopener">
    Open or download the syllabus PDF
  </a>
</p>

<div style="width:100%; height:900px;">
  <iframe
    src="{{{{ '/assets/pdfjs/web/viewer.html?file=' | relative_url }}}}{{{{ page.pdf | relative_url | uri_escape }}}}"
    width="100%"
    height="100%"
    style="border:0;"
  ></iframe>
</div>
"""


def maybe_warn_missing(site_relative_path: str, repo_root: Path) -> None:
    if not CHECK_FILES_EXIST:
        return
    if not site_relative_path.startswith("/"):
        return
    local = repo_root / site_relative_path.lstrip("/")
    if not local.exists():
        print(f"[warn] missing file on disk: {local}")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ----------------------------
# Define your merged bundles here
# ----------------------------
# One bundle = one merged PDF + one thumbnail + one .md page.
#
# Convention:
# - PDF expected at: assets/pdf/UMD_2025/<slug>.pdf
# - IMG expected at: assets/img/UMD_2025/<slug>.png
#
# Example below merges "Modularity 2" + "Modularity 3" into one bundle "modularity".
# Replace readings with the exact set from your syllabus/assignments.
# ----------------------------

BUNDLES: List[Bundle] = [
    Bundle(
        slug="modularity",
        title="UMD 2025 NACS 645: Modularity",
        description="Perceptual modularity, cognitive penetrability, and specialization.",
        importance=1,
        # or actual dates if you prefer
        sessions=["Modularity 2", "Modularity 3"],
        readings=[
            "Pylyshyn, Z. (1999). Is vision continuous with cognition? The case for cognitive impenetrability of visual perception. Behavioral and Brain Sciences, 22, 341–365.",
            "Lupyan, G. (2015). Cognitive penetrability of perception in the age of prediction: Predictive systems are penetrable systems. Review of Philosophy and Psychology, 6, 547–569.",
            "Schalk, G., et al. (2017). Facephenes and rainbows: Causal evidence for functional and anatomical specificity of face and color processing in the human brain. PNAS, 114(46), 12285–12290.",
            "Gomez, J., Barnett, M., & Grill-Spector, K. (2019). Extensive childhood experience with Pokémon suggests eccentricity drives organization of visual cortex. Nature Human Behaviour, 3(6), 611–624.",
        ],
    ),
    Bundle(
        slug="brain_architecture",
        title="UMD 2025 NACS 645: Brain architecture",
        description="Connectivity, network organization, and constraints on computation.",
        importance=2,
        sessions=[
            "Brain architecture 1 (connections)", "Brain architecture 3 (representations)"],
        readings=[
            "Bullmore, E., & Sporns, O. (2012). The economy of brain network organization. Nature Reviews Neuroscience, 13(5), 336-349.",
            "Reimann, M. W., Nolte, M., Scolamiero, M., Turner, K., Perin, R., Chindemi, G., ... & Markram, H. (2017). Cliques of neurons bound into cavities provide a missing link between structure and function. Frontiers in Computational Neuroscience, 11, 48.",
            "Brette, R. (2019). Is coding a relevant metaphor for the brain?. Behavioral and Brain Sciences, 42, e215.",
            "Kriegeskorte, N., & Diedrichsen, J. (2019). Peeling the onion of brain representations. Annual review of neuroscience, 42(1), 407-432.",
        ],
    ),

    Bundle(
        slug="cognitive_architecture",
        title="UMD 2025 NACS 645: Cognitive architecture",
        description="Bayesian approaches to cognition and arguments about their scope and robustness.",
        importance=4,
        sessions=["Cognitive architecture 2 (Bayesian models)"],
        readings=[
            "Tenenbaum, J. B., Kemp, C., Griffiths, T. L., & Goodman, N. D. (2011). How to grow a mind: Statistics, structure, and abstraction. Science, 331, 1279-1285.",
            "Marcus, G. F., & Davis, E. (2013). How robust are probabilistic models of higher-level cognition? Psychological Science, 24, 2351-2360.",
        ],
    ),

    Bundle(
        slug="innateness",
        title="UMD 2025 NACS 645: Innateness",
        description="Origins of knowledge in object cognition and language acquisition debates.",
        importance=5,
        sessions=["Innateness 1 (object concepts)", "Innateness 2 (language)"],
        readings=[
            "Spelke, E. S. (1998). Nativism, empiricism, and the origins of knowledge. Infant Behavior and Development, 21, 181-200.",
            "Johnson, S. P. (2010). How infants learn about the visual world. Cognitive Science, 34, 1158-1184.",
            "Dautriche, I., Goupil, L., Smith, K., & Rabagliati, H. (2021). Knowing what we don’t know: Accurate word learning from an unreliable speaker. Open Mind, 5, 1-19.",
            "Pearl, L. (2022). Poverty of the stimulus without tears. Language Learning and Development, 18(4), 415-454.",
        ],
    ),

    Bundle(
        slug="methods",
        title="UMD 2025 NACS 645: Methods and paradigms",
        description="Theory testing, inference from neuroimaging, and the role of paradigms in explanation.",
        importance=6,
        sessions=["Method 1 (quantitative perspectives)",
                  "Method 2 (need for paradigms)"],
        readings=[
            "Meehl, P. E. (1967). Theory-testing in psychology and physics: A methodological paradox. Philosophy of Science, 34(2), 103-115.",
            "Poldrack, R. A. (2006). Can cognitive processes be inferred from neuroimaging data? Trends in Cognitive Sciences, 10(2), 59-63.",
            "Jolly, E., & Chang, L. J. (2019). The flatland fallacy: Moving beyond low-dimensional thinking. Topics in Cognitive Science, 11(2), 433-454.",
            "Krakauer, J. W., Ghazanfar, A. A., Gomez-Marin, A., MacIver, M. A., & Poeppel, D. (2017). Neuroscience needs behavior: Correcting a reductionist bias. Neuron, 93(3), 480-490.",
        ],
    ),

    Bundle(
        slug="evolution_of_cognition",
        title="UMD 2025 NACS 645: Evolution of cognition",
        description="Evolutionary accounts of syntax and the role of language in cognitive evolution.",
        importance=7,
        sessions=[
            "Evolution of cognition (did language come before or after?)"],
        readings=[
            "Fitch, W. T. (2011). The evolution of syntax: An exaptationist perspective. Frontiers in Evolutionary Neuroscience, 3, 9.",
            "Putt, S. S., Wijeakumar, S., Franciscus, R. G., & Spencer, J. P. (2017). The functional brain networks that underlie early stone tool manufacture. Nature Human Behaviour, 1(6), 0102.",
        ],
    ),

    Bundle(
        slug="social_cognition",
        title="UMD 2025 NACS 645: Social cognition",
        description="Cooperation, origins of social cognition, morality as cooperation and rules, and neural accounts of mentalizing.",
        importance=8,
        sessions=[
            "Social cognition 1 (cooperation)",
            "Social cognition 2 (origins)",
            "Social cognition 3 (moral technologies)",
            "Social cognition 4 (neural need to infer others)",
        ],
        readings=[
            "Rand, D., & Nowak, M. A. (2013). Human cooperation. Trends in Cognitive Sciences, 17, 413-425.",
            "Tan, J., Ariely, D., & Hare, B. (2017). Bonobos respond prosocially toward members of other groups. Scientific Reports, 7(1), 1-11.",
            "Bettle, R., & Rosati, A. G. (2021). The primate origins of human social cognition. Language Learning and Development, 17, 1-18.",
            "de Villiers, J. G., & de Villiers, P. A. (2014). The role of language in theory of mind development. Topics in Language Disorders, 34(4), 313-328.",
            "Hardin, G. (1968). The tragedy of the commons. Science, 162(3859), 1243–1248.",
            "Curry, O. S., Mullins, D. A., & Whitehouse, H. (2019). Is it good to cooperate? Testing the theory of morality-as-cooperation in 60 societies. Current Anthropology, 60(1), 47-69.",
            "Gächter, S., Molleman, L., & Nosenzo, D. (2025). Why people follow rules. Nature Human Behaviour, 1-13.",
            "Koster-Hale, J., & Saxe, R. (2013). Theory of mind: A neural prediction problem. Neuron, 79(5), 836-848.",
            "Joiner, J., Piva, M., Turrin, C., & Chang, S. W. (2017). Social learning through prediction error in the brain. NPJ Science of Learning, 2, 8.",
        ],
    ),

    Bundle(
        slug="social_networks",
        title="UMD 2025 NACS 645: Social networks",
        description="Network structure, information flow, and collective dynamics in social systems.",
        importance=9,
        sessions=["Social networks (beliefs in crowds)"],
        readings=[
            "Guilbeault, D., Becker, J., & Centola, D. (2018). Complex contagions: A decade in review. Complex spreading phenomena in social systems: Influence and contagion in real-world social networks, 3-25.",
            "Wheatley, T., Thornton, M. A., Stolk, A., & Chang, L. J. (2024). The emerging science of interacting minds. Perspectives on Psychological Science, 19(2), 355-373.",
        ],
    ),

    Bundle(
        slug="cognitive_systems",
        title="UMD 2025 NACS 645: Cognitive systems",
        description="Memory and reasoning systems of human cognition.",
        importance=10,
        sessions=["Cognitive systems 1 (reasoning with heuristics and biases)", "Cognitive systems 2 (memory)",
                  ],
        readings=[
            "Tversky, A., & Kahneman, D. (1974). Judgment under uncertainty: Heuristics and biases. Science, 185, 1124–1131.",
            "Gigerenzer, G., & Brighton, H. (2009). Homo heuristicus: Why biased minds make better inferences. Topics in cognitive science, 1(1), 107-143.",
            "Roediger, H.L. III (1990). Implicit memory: retention without remembering. American Psychologist, 45, 1043-1056.",
            "Rugg, M.D. & Yonelinas, A.P. (2003). Human recognition memory: A cognitive neuroscience perspective. Trends in Cognitive Sciences, 7, 313-319.",
        ],
    ),

    Bundle(
        slug="thinking",
        title="UMD 2025 NACS 645: Thinking",
        description="Accounts of reasoning on the individual and collective levels.",
        importance=3,
        sessions=["Thinking 1 (two systems to decide)",
                  "Thinking 2 (model-free vs model-based)", "Thinking 3 (collective knowledge)"],
        readings=[
            "Evans, J. St B. T. (2003). In two minds: dual-process accounts of reasoning. Trends in Cognitive Sciences, 7, 454-459.",
            "Melnikoff, D. E., & Bargh, J. A. (2018). The mythical number two. Trends in Cognitive Sciences, 22(4), 280-293.",
            "Daw, N. D., Niv, Y., & Dayan, P. (2005). Uncertainty-based competition between prefrontal and dorsolateral striatal systems for behavioral control. Nature neuroscience, 8(12), 1704-1711.",
            "Collins, A. G., & Cockburn, J. (2020). Beyond dichotomies in reinforcement learning. Nature Reviews Neuroscience, 21(10), 576-586",
            "Navajas, J., Niella, T., Garbulsky, G., Bahrami, B., & Sigman, M. (2018). Aggregated knowledge from a small number of debates outperforms the wisdom of large crowds. Nature Human Behaviour, 2, 126-132.",
            "Rabb, N., Fernbach, P. M., & Sloman, S. A. (2019). Individual representation in a community of knowledge. Trends in Cognitive Sciences, 23, 891-902.",
        ],
    ),

    Bundle(
        slug="neuroai",
        title="UMD 2025 NACS 645: NeuroAI",
        description="Links between artificial neural systems and biological cognition: models, limits, and interpretations.",
        importance=11,
        sessions=["NeuroAI 1 (is ai part of cognitive science)", "NeuroAI 2 (cognitive properties of llms)",
                  ],
        readings=[
            "Yamins, D. L. K., & DiCarlo, J. J. (2016). Using goal-driven deep learning models to understand sensory cortex. Nature Neuroscience, 19(3), 356–365.",
            "Richards, B. A. et al. (2019). A deep learning framework for neuroscience. Nature Neuroscience, 22(11), 1761–1770.",
            "Palminteri, S., & Pistilli, G. (2025). Navigating Inflationary and Deflationary Claims Concerning Large Language Models Avoiding Cognitive Biases",
            "Silver, D., Singh, S., Precup, D., & Sutton, R. S. (2021). Reward is enough. Artificial intelligence, 299, 103535.",
            "Fedorenko, E., Piantadosi, S. T., & Gibson, E. A. (2024). Language is primarily a tool for communication rather than thought. Nature, 630(8017), 575-586",
        ],
    ),
]


def main() -> None:
    repo_root = Path(".").resolve()

    # Write syllabus page
    syllabus_path = OUTPUT_DIR / f"2025_UMD_course_{SYLLABUS_SLUG}.md"
    write_text(syllabus_path, md_for_syllabus())
    print(f"[ok] wrote {syllabus_path}")
    maybe_warn_missing(SYLLABUS_PDF, repo_root)
    maybe_warn_missing(SYLLABUS_IMG, repo_root)

    # Write bundle pages
    for b in BUNDLES:
        outpath = OUTPUT_DIR / f"2025_UMD_course_{b.slug}.md"
        write_text(outpath, md_for_bundle(b))
        print(f"[ok] wrote {outpath}")

        # Check expected files exist
        maybe_warn_missing(f"{PDF_BASE}/{b.slug}.pdf", repo_root)
        maybe_warn_missing(f"{IMG_BASE}/{b.slug}.png", repo_root)

    print("[done] generation complete.")


if __name__ == "__main__":
    main()
