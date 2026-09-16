# yata

**yazi's navigation, as a native desktop app.**

yata is a modal, keyboard-first GTK4 file manager for Linux. It takes the
navigation model of [yazi](https://github.com/sxyazi/yazi) — Miller columns,
modal input, operators and counts — and runs it as a real Wayland desktop
application instead of inside a terminal, so drag-and-drop, thumbnails, the
XDG file chooser and "Open file location" all work the way the rest of the
desktop expects.

## Why this exists

yazi has the best navigation model of any file manager. But living in a
terminal costs you the things a desktop file manager is for: you cannot drag a
file into a browser upload field, image previews depend on terminal graphics
protocols, and no other application can hand you a file through it.

Conversely, GUI file managers have the desktop integration but ask you to
reach for the mouse.

yata is the intersection.

## Status

Early. yata is a hard fork of [Strata](https://github.com/lgse/strata) 0.18.0,
which already provides the hard, unglamorous two-thirds of a file manager:

- Miller-column, Icons and List browsing, virtualized to 100k entries
- Drag-and-drop, in and out, via `GdkFileList`
- Previews and thumbnails for text, source, images, camera RAW, PDF, audio and
  video, with every native parser isolated out-of-process under Bubblewrap
- GIO/GVfs remote locations, trash, undo, cancellable directory loading
- XDG desktop portal file chooser and `org.freedesktop.FileManager1`
- Theming, including live Omarchy Quattro following

What yata adds on top is the modal input layer.

### Roadmap

| Capability | State |
| --- | --- |
| Miller columns behaving like yazi's (fixed strip that shifts) | in progress |
| `hjkl` / `gg` / `G` motions | partial, inherited |
| Counts and operators (`3j`, `dd`, `yy`, `p`) | planned |
| Visual mode (`v` / `V`) | planned |
| `:` command mode, `;` shell on selection | planned |
| Bulk rename through `$EDITOR` | planned |
| Tabs | planned |
| Configurable keymap (`keymap.toml`) | planned |
| Task queue with visible progress | planned |
| Lua plugin API | undecided |

## Build

The toolchain is pinned with [mise](https://mise.jdx.dev); `mise trust` once,
then:

```bash
mise run dev            # build and launch
mise run build          # release binary
mise run check          # fmt, compile, clippy, test, deny, typos
mise run install-local  # per-user binary, icon, and desktop entry
```

Runtime dependencies on Arch:

```bash
sudo pacman -S --needed base-devel bubblewrap ffmpeg ffmpegthumbnailer \
  fontconfig gst-libav gst-plugins-good gtk4 gtksourceview5 poppler-glib
```

GTK 4.12+ and glibc 2.39+ are required.

## Relationship to Strata

yata is a fork, not a competitor. Strata is an excellent GUI file manager that
happens to be the ideal base for this; upstream stays wired up as the `upstream`
remote so fixes can be pulled in:

```bash
git fetch upstream && git merge upstream/main
```

Internal asset names (`strata-*.svg`) are deliberately left alone to keep those
merges cheap. Only the user-facing identity — binary, application ID, desktop
entry, D-Bus names, config directory — was renamed.

## License

MIT. Copyright (c) 2026 melandur for yata and its modifications; copyright (c)
2026 LGSE Ltd. for Strata, the original work. See [LICENSE](LICENSE).
