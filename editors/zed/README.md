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


If Liza suddenly loses highlighting, inspect Zed's log for a query loading
error. The queries and the pinned grammar must agree: adding keywords such as
`borrow` or `mut` to highlights without updating the grammar revision makes
Zed reject the entire language. `python3 tools/check_editor.py` now checks
the pinned parser against the worktree before compiling the queries; CI fetches
history for this check. After updating a dev extension, use **Rebuild** in Zed's
Extensions view (or reinstall the same dev extension directory) to reload it.
