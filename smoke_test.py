from app import app

with app.test_client() as c:
    r = c.get('/')
    print('GET / status:', r.status_code)
    body = r.data.decode()
    checks = [
        ('hero section',     'id="hero"'     in body),
        ('about section',    'id="about"'    in body),
        ('projects section', 'id="projects"' in body),
        ('contact section',  'id="contact"'  in body),
        ('CSS link',         'style.css'     in body),
        ('JS link',          'main.js'       in body),
        ('Nav logo',         'nav-logo'      in body),
    ]
    all_ok = True
    for label, ok in checks:
        status = 'OK  ' if ok else 'FAIL'
        print(f'  {status} - {label}')
        if not ok:
            all_ok = False
    print('All checks passed!' if all_ok else 'Some checks FAILED')
