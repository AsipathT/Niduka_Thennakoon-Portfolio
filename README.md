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
