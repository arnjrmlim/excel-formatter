# GitHub Readiness Checklist

- [x] Repository structure audited.
- [x] Unnecessary generated files removed.
- [x] Sensitive files scanned.
- [x] No hardcoded secrets found.
- [x] `.gitignore` configured.
- [x] Documentation created.
- [x] Dependencies documented.
- [x] Security policy created.
- [x] Contributing guide created.
- [x] License selected and added.
- [ ] Optional code quality refactors completed.
- [x] Release artifact process documented.
- [x] Ready for first commit after final review.

## Notes

- IMS TinyTask downloads use `https://github.com/arnjrmlim/ims-format/releases/latest/download/IMS_tinytask.exe`.
- Keep executable builds out of Git and publish them through GitHub Releases with the exact asset name `IMS_tinytask.exe`.
- Consider splitting `Formatter.html` into separate HTML, CSS, and JavaScript files after publication.
