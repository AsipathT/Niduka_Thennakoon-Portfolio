/**
 * main.js – Niduka Thennakoon Portfolio
 * Handles: theme toggle, mobile nav, typing effect,
 *          scroll-reveal, project filter, contact form AJAX,
 *          active nav link on scroll, footer year.
 */

(function () {
  'use strict';

  /* ── Helpers ──────────────────────────────────────────────────────────── */
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /* ── Theme toggle ─────────────────────────────────────────────────────── */
  const html        = document.documentElement;
  const themeToggle = $('#theme-toggle');

  // Load saved preference or default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  html.setAttribute('data-theme', savedTheme);

  themeToggle?.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    const next    = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  });

  /* ── Mobile nav ───────────────────────────────────────────────────────── */
  const navToggle  = $('#nav-toggle');
  const mobileMenu = $('#mobile-menu');

  navToggle?.addEventListener('click', () => {
    const isOpen = mobileMenu.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', isOpen);
    mobileMenu.setAttribute('aria-hidden', !isOpen);
    // Update tabindex on mobile links
    $$('.nav-link', mobileMenu).forEach(a =>
      a.setAttribute('tabindex', isOpen ? '0' : '-1')
    );
  });

  // Close mobile menu when a link is clicked
  $$('.nav-link', mobileMenu).forEach(link => {
    link.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      navToggle?.setAttribute('aria-expanded', 'false');
      mobileMenu.setAttribute('aria-hidden', 'true');
    });
  });

  /* ── Typing effect ────────────────────────────────────────────────────── */
  const typedEl = $('#typed-text');
  // TODO: customise these roles to match your specialisations
  const roles = [
    'build web apps',
    'write clean code',
    'solve hard problems',
    'love open source',
  ];
  let roleIdx = 0;
  let charIdx = 0;
  let deleting = false;
  const typeSpeed   = 80;   // ms per character when typing
  const deleteSpeed = 40;   // ms per character when deleting
  const pauseAfter  = 1800; // ms to pause at end of word

  function type() {
    if (!typedEl) return;
    const current = roles[roleIdx];

    if (!deleting) {
      typedEl.textContent = current.slice(0, charIdx + 1);
      charIdx++;
      if (charIdx === current.length) {
        deleting = true;
        setTimeout(type, pauseAfter);
        return;
      }
    } else {
      typedEl.textContent = current.slice(0, charIdx - 1);
      charIdx--;
      if (charIdx === 0) {
        deleting = false;
        roleIdx  = (roleIdx + 1) % roles.length;
      }
    }
    setTimeout(type, deleting ? deleteSpeed : typeSpeed);
  }
  setTimeout(type, 600);

  /* ── Scroll-reveal (IntersectionObserver) ─────────────────────────────── */
  const revealEls = $$('.reveal');
  const observer  = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target); // fire once
        }
      });
    },
    { threshold: 0.12 }
  );
  revealEls.forEach(el => observer.observe(el));

  /* ── Active nav link on scroll ────────────────────────────────────────── */
  const sections = $$('section[id]');
  const navLinks  = $$('.nav-links .nav-link');

  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          navLinks.forEach(link => {
            link.classList.toggle(
              'active',
              link.getAttribute('href') === `#${entry.target.id}`
            );
          });
        }
      });
    },
    { rootMargin: `-${getComputedStyle(html).getPropertyValue('--nav-h')} 0px -55% 0px` }
  );
  sections.forEach(s => sectionObserver.observe(s));

  /* ── Project filter ───────────────────────────────────────────────────── */
  const filterBtns = $$('.filter-btn');
  const cards      = $$('.project-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      cards.forEach(card => {
        const show = filter === 'all' || card.dataset.category === filter;
        card.setAttribute('aria-hidden', !show);
        // Fade in/out via CSS transition
        card.style.opacity    = show ? '1' : '0';
        card.style.pointerEvents = show ? '' : 'none';
        // We use aria-hidden to hide with display:none via CSS
      });
    });
  });

  /* ── Contact form (AJAX) ──────────────────────────────────────────────── */
  const form       = $('#contact-form');
  const statusBox  = $('#form-status');
  const submitBtn  = $('#submit-btn');

  function setFieldError(input, msg) {
    const errorEl = input.closest('.form-group')?.querySelector('.field-error');
    if (errorEl) errorEl.textContent = msg;
    if (msg) input.classList.add('invalid');
    else     input.classList.remove('invalid');
  }

  function validateForm(data) {
    let valid = true;
    const name    = form.querySelector('#name');
    const email   = form.querySelector('#email');
    const message = form.querySelector('#message');

    // Reset
    [name, email, message].forEach(el => setFieldError(el, ''));

    if (!data.name.trim()) {
      setFieldError(name, 'Name is required.');
      valid = false;
    }
    if (!data.email.trim() || !data.email.includes('@')) {
      setFieldError(email, 'A valid email address is required.');
      valid = false;
    }
    if (!data.message.trim()) {
      setFieldError(message, 'Message cannot be empty.');
      valid = false;
    }
    return valid;
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const data = {
      name:    form.querySelector('#name').value,
      email:   form.querySelector('#email').value,
      message: form.querySelector('#message').value,
    };

    if (!validateForm(data)) return;

    // Show loading state
    const btnText    = submitBtn.querySelector('.btn-text');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');
    btnText.textContent = 'Sending…';
    btnSpinner.classList.remove('hidden');
    submitBtn.disabled = true;

    statusBox.className = 'form-status hidden';
    statusBox.textContent = '';

    try {
      const res  = await fetch('/contact', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(data),
      });
      const json = await res.json();

      if (json.ok) {
        statusBox.textContent = json.message || 'Message sent!';
        statusBox.className   = 'form-status success';
        form.reset();
      } else {
        const msgs = (json.errors || ['Something went wrong.']).join(' ');
        statusBox.textContent = msgs;
        statusBox.className   = 'form-status error';
      }
    } catch {
      statusBox.textContent = 'Network error. Please try again.';
      statusBox.className   = 'form-status error';
    } finally {
      btnText.textContent = 'Send Message';
      btnSpinner.classList.add('hidden');
      submitBtn.disabled  = false;
    }
  });

  /* ── Footer year ──────────────────────────────────────────────────────── */
  const yearEl = $('#footer-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

})();
