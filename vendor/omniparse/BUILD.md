# Re-vendoring Omniparse

This directory contains a self-contained build of `@tyroneross/omniparse`. The
dist is committed and ready to run — no install step needed. Re-vendor only
when you want to pick up upstream changes.

## Procedure

```bash
# 1. Copy the upstream SDK to a scratch dir (so we don't mutate the source repo).
rm -rf /tmp/omniparse-vendor-build
mkdir -p /tmp/omniparse-vendor-build
cp -r ~/Desktop/git-folder/Omniparse/packages/sdk/* /tmp/omniparse-vendor-build/
mkdir -p /tmp/omniparse-vendor-build/vendor
cp ~/Desktop/git-folder/Omniparse/vendor/xlsx-0.20.3.tgz /tmp/omniparse-vendor-build/vendor/

# 2. Fix the xlsx path and inline all deps (scratch copy only — do NOT commit to upstream).
cd /tmp/omniparse-vendor-build
sed -i '' 's|file:../../vendor/xlsx|file:./vendor/xlsx|' package.json

# Replace tsup.config.ts with an inlined variant:
cat > tsup.config.ts <<'EOF'
import { defineConfig } from 'tsup';
export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'parsers/index': 'src/parsers/index.ts',
    'bin/omniparse': 'bin/omniparse.ts',
  },
  format: ['cjs', 'esm'],
  dts: false,
  clean: true,
  sourcemap: false,
  splitting: false,
  target: 'node18',
  noExternal: [/.*/],
});
EOF

# 3. Install and build.
npm install
npm run build

# 4. Verify the dist has no external runtime requires.
grep -cE 'require\("(xlsx|sax|p-limit)"\)' dist/bin/omniparse.js
# Expected output: 0

# 5. Copy the fresh dist into this vendor directory.
VENDOR=~/Desktop/git-folder/research/vendor/omniparse
rm -rf "$VENDOR/dist"
mkdir -p "$VENDOR/dist"
cp -r dist/* "$VENDOR/dist/"
chmod +x "$VENDOR/dist/bin/omniparse.js" "$VENDOR/dist/bin/omniparse.mjs"

# 6. Refresh the LICENSE copy and update .upstream metadata.
cp ~/Desktop/git-folder/Omniparse/LICENSE "$VENDOR/LICENSE"
# Hand-edit .upstream to bump upstream_commit, upstream_version, vendored_on.
```

## What not to do

- Do NOT commit the modified `tsup.config.ts` back to the Omniparse upstream
  repo. The inlining is a vendoring-only transformation.
- Do NOT add `node_modules/` to research's git. The dist is self-contained; a
  frozen node_modules would be multiple MBs of dead weight.
- Do NOT edit files under `vendor/omniparse/dist/` by hand. Always rebuild.
