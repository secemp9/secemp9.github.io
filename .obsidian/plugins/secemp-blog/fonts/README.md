# Bundled blog fonts

Unmodified font binaries from [Google Fonts](https://github.com/google/fonts),
commit `f2bd09badbc763d8757951d52deec29da27e85fb`:

- `ofl/newsreader/Newsreader[opsz,wght].ttf` → `Newsreader-Regular.ttf`
- `ofl/newsreader/Newsreader-Italic[opsz,wght].ttf` → `Newsreader-Italic.ttf`
- `ofl/ibmplexmono/IBMPlexMono-Regular.ttf`
- `ofl/ibmplexmono/IBMPlexMono-Medium.ttf`

Newsreader retains its optical-size and weight axes. Both families use the SIL
Open Font License 1.1; the corresponding copyright notices and licenses are in
`Newsreader-OFL.txt` and `IBMPlexMono-OFL.txt`.

Blog loads these files into Obsidian's font set directly from the vault. They
are not installed system-wide and do not add network requests while writing.
