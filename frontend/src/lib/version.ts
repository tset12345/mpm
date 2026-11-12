// next.config.js가 빌드할 때 값을 넣는다 (package.json 버전, 빌드 커밋 7자리).
export const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION ?? "";
export const COMMIT_SHA = process.env.NEXT_PUBLIC_COMMIT_SHA ?? "";

/** "v2.0.0 · abc1234" 형태. 버전이 없으면 null을 돌려 표시하지 않는다. */
export function formatVersion(version: string, commit: string): string | null {
  if (!version) return null;
  return commit ? `v${version} · ${commit}` : `v${version}`;
}
