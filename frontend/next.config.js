const { execSync } = require("node:child_process");
const { version } = require("./package.json");

// 화면에 표시할 빌드 커밋. Vercel은 빌드 환경변수로 제공하고, 로컬은 git에서 읽는다.
function buildCommit() {
  const fromVercel = process.env.VERCEL_GIT_COMMIT_SHA;
  if (fromVercel) return fromVercel.slice(0, 7);
  try {
    return execSync("git rev-parse --short=7 HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "";
  }
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: version,
    NEXT_PUBLIC_COMMIT_SHA: buildCommit(),
  },
};

module.exports = nextConfig;
