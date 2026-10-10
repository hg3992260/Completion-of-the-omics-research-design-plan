#!/bin/bash
# macOS 分发辅助：为内嵌的 opencode 内核签名 + 去 quarantine。
#
# 为什么要做：
#   - 从网上下载/解包的 opencode 带 com.apple.quarantine，Gatekeeper 会拦；
#   - Bun/JSC 运行需要 JIT，在 Hardened Runtime 下必须带相应 entitlement，
#     否则内嵌二进制一启动就崩；
#   - .app 内任何可执行被改动后，外层签名会失效，必须重新签。
#
# 用法：
#   ./macos_sign_kernel.sh "Developer ID Application: 你的名字 (TEAMID)" path/to/PCLRadiomics.app
#   # 可选公证：
#   xcrun notarytool submit PCLRadiomics.dmg --keychain-profile <profile> --wait
#   xcrun stapler staple PCLRadiomics.app
set -euo pipefail

IDENTITY="${1:?第1个参数：签名身份（如 Developer ID Application: XXX (TEAMID)）}"
APP="${2:?第2个参数：.app 路径}"

ENT_DIR="$(mktemp -d)"
ENT="$ENT_DIR/opencode.entitlements"
cat > "$ENT" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-jit</key><true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
  <key>com.apple.security.cs.disable-library-validation</key><true/>
</dict>
</plist>
PLIST

# 内核二进制可能落在 Resources/opencode 或 Frameworks 下，逐个候选找
for KERNEL in \
  "$APP/Contents/Resources/opencode/opencode" \
  "$APP/Contents/Frameworks/opencode/opencode" \
  "$APP/Contents/MacOS/opencode/opencode"; do
  if [ -f "$KERNEL" ]; then
    echo "签名内核：$KERNEL"
    xattr -dr com.apple.quarantine "$KERNEL" 2>/dev/null || true
    codesign --force --options runtime --entitlements "$ENT" --sign "$IDENTITY" "$KERNEL"
  fi
done

echo "重签外层 app：$APP"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
codesign --force --deep --options runtime --sign "$IDENTITY" "$APP"
codesign --verify --verbose=2 "$APP"
echo "完成。下一步可 notarytool 公证并 stapler staple。"
