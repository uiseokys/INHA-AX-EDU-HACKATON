#!/bin/sh
# 템플릿에 쓰인 Tailwind 클래스를 읽어 app/static/app.css 를 다시 만듭니다. (Node.js 필요)
# 화면의 클래스나 색을 바꾼 뒤에만 실행하면 됩니다. 앱 실행에는 Node.js가 필요 없습니다.
cd "$(dirname "$0")/.." || exit 1
npm install --no-save --no-package-lock --silent tailwindcss@4 @tailwindcss/cli@4 || exit 1
npx @tailwindcss/cli -i app/static/src/input.css -o app/static/app.css --minify
