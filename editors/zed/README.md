# Liza for Zed

In Zed run **`zed: install dev extension`** and select this directory
(`editors/zed`, not the repository root). Open any `.liza` file.
Zed downloads the pinned Tree-sitter grammar and builds it automatically;
Node.js is not needed to use the extension. Internet access is needed on first
installation. See [Zed's development guide](https://zed.dev/docs/extensions/developing-extensions).

Includes syntax highlighting, bracket matching, indentation, line comments,
and an outline for functions, structs and enums. This is not an LSP: semantic
diagnostics and completion are not included. Editor parsing is intentionally
permissive during incomplete edits; the Liza compiler defines valid programs.

Grammar sources and generated C parser live in `../tree-sitter-liza`.
To update the grammar, regenerate and test it, commit the generated parser,
then pin `[grammars.liza].rev` in `extension.toml` to that commit.
The manifest's `path` selects the grammar directory inside the Liza repository.
For unpublished grammar changes, a local Git repository `file://` URL can be
used with a committed revision, as described in the Zed documentation.
