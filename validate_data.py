import json, sys

files = ['data/projects.json', 'data/site_config.json']
for f in files:
    try:
        with open(f, encoding='utf-8') as fh:
            data = json.load(fh)
        if f == 'data/projects.json':
            print("OK  {} - {} projects".format(f, len(data)))
            for p in data:
                print("    [{}] {}".format(p['domain'], p['title']))
        else:
            keys = list(data.keys())
            print("OK  {} - keys: {}".format(f, keys))
    except Exception as e:
        print("FAIL {}: {}".format(f, e))
        sys.exit(1)

print("\nAll JSON files valid.")
