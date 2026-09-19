#!/usr/bin/env bash
# 把 dist/PCLRadiomics.app 打成可拖拽安装的 dmg（仅在 macOS 上可运行）。
#
#   ./make_dmg.sh                 # 版本号默认 1.0.0，架构取 `uname -m`
#   PCL_VERSION=1.2.0 ./make_dmg.sh
#
# 产物：PCLRadiomics-<版本>-macos-<架构>.dmg
# 打开后是「左侧应用图标 + 右侧 Applications 快捷方式」的经典拖拽界面。
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${PCL_VERSION:-1.0.0}"
ARCH="$(uname -m)"
APP="dist/PCLRadiomics.app"
STAGE="build_dmg"
OUT="PCLRadiomics-${VERSION}-macos-${ARCH}.dmg"
VOLNAME="PCL-Radiomics"

if [[ ! -d "$APP" ]]; then
  echo "找不到 $APP，请先打包："
  echo "  python -m PyInstaller --noconfirm --clean pclradiomics_macos.spec"
  exit 1
fi

echo "== 准备 dmg 内容 =="
rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"          # 拖拽安装用的快捷方式

# 顺带把说明书放进去
if [[ -f README.md ]]; then
  cp README.md "$STAGE/使用说明.md" 2>/dev/null || cp README.md "$STAGE/README.md"
fi

echo "== 生成 dmg（压缩格式 UDZO）=="
hdiutil create -volname "$VOLNAME" -srcfolder "$STAGE" -ov -format UDZO "$OUT"

echo "== 校验 =="
hdiutil verify "$OUT" | tail -2
SHA="$(shasum -a 256 "$OUT" | awk '{print $1}')"
echo "$SHA  $OUT" > "${OUT}.sha256"
rm -rf "$STAGE"

echo
echo "完成：$OUT"
echo "SHA256：$SHA"
echo
echo "提示：本 dmg 未做 Apple 签名/公证，首次打开若被 Gatekeeper 拦截，"
echo "     可右键点应用 → 打开，或执行： xattr -dr com.apple.quarantine /Applications/PCLRadiomics.app"
