<<<<<<< HEAD
# Niduka Thennakoon – Portfolio

A modern, dark-themed personal portfolio website built with **Flask + Jinja2** and pure **HTML/CSS/JS**.

## ✨ Features
- Dark / Light theme toggle (persisted in `localStorage`)
- Animated typing headline (vanilla JS)
- Scroll-reveal animations via `IntersectionObserver`
- Filterable project cards (driven by `data/projects.json`)
- Responsive, mobile-first layout
- Working contact form (AJAX → Flask → SMTP)
- Accessible: semantic HTML, ARIA labels, keyboard navigation, reduced-motion support
- Optional: Frozen-Flask static export for free hosting

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/NidukaThennakoon/portfolio.git
cd portfolio

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your SMTP credentials

# 5. Run the development server
python app.py
# → Open http://127.0.0.1:5000
```

## 📁 Project Structure

```
Niduka_Thennakoon-Portfolio/
├── app.py                  # Flask app + contact route
├── data/
│   └── projects.json       # Add your projects here
├── templates/
│   ├── base.html           # Layout (nav, footer, fonts)
│   ├── index.html          # Single-page composition
│   └── partials/           # One file per section
│       ├── nav.html
│       ├── hero.html
│       ├── about.html
│       ├── skills.html
│       ├── projects.html
│       ├── experience.html
│       ├── contact.html
│       └── footer.html
├── static/
│   ├── css/style.css       # All styles, CSS variables, responsive
│   ├── js/main.js          # Theme, typing, scroll-reveal, filter, form
│   └── images/             # Place your photos here
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 📝 Adding a Project

Edit `data/projects.json` and add an object:

```json
{
  "id": 4,
  "title": "My New Project",
  "description": "What it does and why it matters.",
  "image": "/static/images/my-project.png",
  "tags": ["Python", "Flask"],
  "category": "web",
  "github": "https://github.com/NidukaThennakoon/my-project",
  "live": "https://my-project.vercel.app"
}
```

Restart Flask (or the page auto-reloads in debug mode) — done!

## 🌐 Static Export (Frozen-Flask)

```bash
# In a Python shell or separate freeze.py script:
from flask_frozen import Freezer
from app import app
freezer = Freezer(app)
freezer.freeze()   # outputs to /build
```

Deploy the `/build` folder to GitHub Pages, Netlify, or Vercel for free hosting.

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask session secret (change before production) |
| `MAIL_SERVER` | SMTP host (e.g. `smtp.gmail.com`) |
| `MAIL_PORT` | SMTP port (e.g. `587`) |
| `MAIL_USE_TLS` | `True` or `False` |
| `MAIL_USERNAME` | Sender email address |
| `MAIL_PASSWORD` | App password (not your login password) |
| `MAIL_RECIPIENT` | Where contact form emails are delivered |

## 📄 License

MIT © 2025 Niduka Thennakoon
=======
# Niduka Thennakoon | Portfolio

Personal portfolio of **[Your Name]**, Associate Software Engineer and Software Engineering student at **SLIIT**. It showcases my projects, skills, and experience, built with Python and Flask.

🔗 **Live site:** [your-live-link-here]

---

## About

I'm a software engineer in the making, focused on [your focus, e.g. full-stack development, backend, AI]. I build practical projects, keep learning fast, and aim to grow into a founder who creates products that matter.

## Features

- Responsive design for mobile, tablet, and desktop
- Projects section driven by data, so adding a new project is quick
- Skills and experience timeline
- Contact form / contact links
- Clean, fast, and easy to customize

## Tech Stack

| Area | Tools |
|------|-------|
| Backend | Python, Flask, Jinja2 |
| Frontend | HTML5, CSS3, JavaScript |
| Deployment | [Render / Vercel / Netlify / GitHub Pages] |
| Version Control | Git, GitHub |

## Project Structure

```
yourname-portfolio/
├── app.py
├── templates/
│   ├── base.html
│   └── index.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/[your-username]/[repo-name].git
cd [repo-name]

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Featured Projects

| Project | Description | Tech |
|---------|-------------|------|
| [Project 1] | [One line on what it does and the result] | [Stack] |
| [Project 2] | [One line on what it does and the result] | [Stack] |
| [Project 3] | [One line on what it does and the result] | [Stack] |

## Contact

- 📧 Email: nidukavikumasipath@gmail.com
- 💼 LinkedIn: https://www.linkedin.com/in/niduka-thennakoon-323055240
- 🐙 GitHub: https://github.com/AsipathT

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

⭐ If you like this portfolio, feel free to star the repo!
>>>>>>> 271009bfacc63ae7e9824982334b515ebbc24ca8
