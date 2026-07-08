// ライト/ダークテーマの選択と適用。選択は localStorage に保存し、
// system 選択時は OS の prefers-color-scheme に追従する。

export type ThemeChoice = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "cbs:theme";
export const THEME_ORDER: readonly ThemeChoice[] = ["light", "dark", "system"];

// FOUC (初回描画時のちらつき) 回避用。<head> でペイント前に実行するインラインスクリプト。
// localStorage の選択 (既定 system) を読み、<html> に .dark を付与する。
export const THEME_INIT_SCRIPT = `(function(){try{var c=localStorage.getItem('${THEME_STORAGE_KEY}')||'system';var d=c==='dark'||(c==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

/** 選択から「ダークにするか」を解決する (system は OS 設定を見る)。 */
export function resolveDark(choice: ThemeChoice): boolean {
  if (choice === "system") {
    return (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }
  return choice === "dark";
}

/** <html> の .dark クラスを選択に合わせて更新する。 */
export function applyTheme(choice: ThemeChoice): void {
  document.documentElement.classList.toggle("dark", resolveDark(choice));
}
