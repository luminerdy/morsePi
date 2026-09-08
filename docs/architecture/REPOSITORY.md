# Repository Map

```text
morsepi/
  app.py                 Flask routes and station runtime
  learning/              Progress, attempt recording, rhythm coaching
  messaging/             Local messages and station-side cloud delivery
  students/              Profiles and stable identities
  storage/               Durable file access and data paths
  security/              Browser request protection
  services/              Family activity reporting
  morse/                 Codec and visual formatting
  templates/             Flask pages
  static/                Browser JavaScript and CSS
scripts/                 Operational commands and installation helpers
cloud/                   AWS-side routing and policy templates
systemd/                 Station services and timers
tests/                   Regression bank
config/                  Tracked configuration examples and registry
data/                    Local runtime data; never relocate during code cleanup
docs/                    Product, user, builder, and admin guides
specs/                   Requirements and implementation status
app.py                   Compatible station launcher
```

## Compatibility Transition

Other root Python files are tiny import bridges, not duplicate implementations.
They alias the actual package module so mutable state is shared. They remain
because older installed updaters compile a fixed list of root files after
fetching a release. Remove them only after all stations have a package-aware
updater, and revise its legacy check list at the same time.

The app still launches with `python3 app.py`; `python3 -m morsepi.app` is also
supported. The Flask asset URLs remain `/static/...`. Data defaults to the
repository-root `data/`, with MORSE_DATA_DIR still honored. Registry fallback
stays under root `config/`. This reorganization changes no student-data schema.

Package initializers are side-effect free. Importing a storage or messaging
module must not start Flask or GPIO. Lambda packaging includes only its required
package files, not the station app or browser assets.

The app remains a single route/runtime module for now. This change establishes
ownership folders, not the blueprint/service rewrite proposed in the rebuild plan.
