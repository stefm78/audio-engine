# Voice Lab Pages

GitHub Pages is only the human listening surface for Voice Casting Lab.

Source of truth remains the successful GitHub Actions artifact referenced by `request.json`.

Rules:

- publisher workflow lives on `main`;
- publication request must point to one successful run in this repository;
- artifact name must start with `voice-casting-`;
- the artifact must contain `index.html`;
- Pages publishes only the current listening bundle;
- generated audio is not committed to the source repository;
- Pages is public, so do not publish confidential/proprietary anchors or media;
- published pages get `noindex,nofollow` as a courtesy, not an access-control mechanism;
- human results continue to export locally as JSON;
- Pages publication is not production promotion and has no effect on the production renderer.

`request.json` stays disabled between tests. After a technical PASS, update it to the exact run id and artifact name. The trusted `main` workflow validates and deploys that artifact.
