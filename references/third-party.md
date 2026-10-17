# Third-party components

Vendored files shipped with this skill. They are copied unmodified (line endings normalised to LF) and pinned
to an exact version.

## Lism CSS

- Package: `lism-css` (npm)
- Version: 1.0.1
- npm dist.integrity: `sha512-goLmDj4P+EYJqoefMPfVzdq6mNbjKK7lEGxYl0dZZzguk0C1kg9bumgCAKwrJOnG1vwVQhgvVa/+xhK03P/k7Q==`
- Source path in the tarball: `package/dist/css/main.css` (the stylesheet the package README loads via CDN)
- Committed as: `assets/lism-css-1.0.1.min.css`
- sha256: `04e9113e6f5dc92ab4fe0b95e81bc74eecb1ff4be27f4c9291147804c7c0ece1`
- Minification: the package ships `dist/css/main.css` already minified (single line, no trailing newline) and has
  no separate `.min.css` sibling; the file was copied as is. The `.min` in the committed name is a naming
  convention only.
- Use: inlined into the HTML report inside its own `<style>` element; the report uses only its layout classes
  (`is--wrapper`, `has--gutter`, `l--flow`).
- Licence: MIT, text below (verbatim from `package/LICENSE`).

```text
MIT License

Copyright (c) Loos, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
